import unittest

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend import models  # noqa: F401
from backend.database import Base
from backend.models.empresa import Empresa
from backend.models.oportunidade import Oportunidade
from backend.schemas.oportunidade import OportunidadeResponse, OportunidadeTagsRequest
from backend.schemas.tag import TagCreate, TagUpdate
from backend.services import oportunidade_service, tag_service


class TagServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        tabelas = [
            Base.metadata.tables[nome]
            for nome in ("empresa", "tag", "oportunidade", "oportunidade_tag")
        ]
        Base.metadata.create_all(self.engine, tables=tabelas)
        self.db = Session(self.engine)
        for emp_id in (1, 2):
            self.db.add(Empresa(empId=emp_id, empNome=f"Empresa {emp_id}"))
        self.db.add(Oportunidade(opoId=10, opoEmpId=1, opoTitulo="Lead"))
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _tag(self, nome: str = "VIP", cor: str = "#2563EB", empresa: int = 1):
        return tag_service.create_tag(self.db, TagCreate(tagNome=nome, tagCor=cor), empresa)

    def _vincular(self, *tag_ids: int) -> OportunidadeResponse:
        return oportunidade_service.set_tags(
            self.db, 10, OportunidadeTagsRequest(tagIds=list(tag_ids)), 1
        )

    def test_cor_precisa_ser_hexadecimal(self) -> None:
        for cor in ("azul", "#FFF", "#GGGGGG", ""):
            with self.subTest(cor=cor), self.assertRaises(ValidationError):
                TagCreate(tagNome="VIP", tagCor=cor)

    def test_nome_vazio_e_recusado(self) -> None:
        with self.assertRaises(ValidationError):
            TagCreate(tagNome="   ", tagCor="#2563EB")

    def test_nome_repetido_na_empresa_e_recusado_sem_diferenciar_maiusculas(self) -> None:
        self._tag("VIP")
        with self.assertRaises(HTTPException) as erro:
            self._tag(" vip ")
        self.assertEqual(erro.exception.status_code, 409)

    def test_mesmo_nome_em_outra_empresa_e_permitido(self) -> None:
        self._tag("VIP", empresa=1)
        self.assertEqual(self._tag("VIP", empresa=2).tagEmpId, 2)

    def test_renomear_para_nome_de_outra_tag_e_recusado(self) -> None:
        self._tag("VIP")
        outra = self._tag("Indicação")
        with self.assertRaises(HTTPException) as erro:
            tag_service.update_tag(self.db, outra.tagId, TagUpdate(tagNome="vip"), 1)
        self.assertEqual(erro.exception.status_code, 409)

    def test_editar_a_cor_mantendo_o_nome_e_permitido(self) -> None:
        tag = self._tag("VIP")
        editada = tag_service.update_tag(
            self.db, tag.tagId, TagUpdate(tagNome="VIP", tagCor="#DC2626"), 1
        )
        self.assertEqual(editada.tagCor, "#DC2626")

    def test_vincular_devolve_tags_em_ordem_de_nome(self) -> None:
        vip = self._tag("VIP")
        indicacao = self._tag("Indicação")
        resposta = self._vincular(vip.tagId, indicacao.tagId)
        self.assertEqual([t.tagNome for t in resposta.tags], ["Indicação", "VIP"])

    def test_vincular_substitui_a_selecao_anterior(self) -> None:
        vip = self._tag("VIP")
        indicacao = self._tag("Indicação")
        self._vincular(vip.tagId)
        resposta = self._vincular(indicacao.tagId)
        self.assertEqual([t.tagId for t in resposta.tags], [indicacao.tagId])

    def test_lista_vazia_remove_as_tags(self) -> None:
        self._vincular(self._tag().tagId)
        self.assertEqual(self._vincular().tags, [])

    def test_ids_repetidos_nao_duplicam_o_vinculo(self) -> None:
        vip = self._tag()
        self.assertEqual(len(self._vincular(vip.tagId, vip.tagId).tags), 1)

    def test_tag_de_outra_empresa_e_recusada(self) -> None:
        de_fora = self._tag("VIP", empresa=2)
        with self.assertRaises(HTTPException) as erro:
            self._vincular(de_fora.tagId)
        self.assertEqual(erro.exception.status_code, 400)

    def test_tag_inativa_nao_pode_ser_vinculada(self) -> None:
        tag = self._tag()
        tag_service.set_tag_ativo(self.db, tag.tagId, False, 1)
        with self.assertRaises(HTTPException) as erro:
            self._vincular(tag.tagId)
        self.assertEqual(erro.exception.status_code, 400)

    def test_inativar_esconde_do_lead_e_reativar_devolve(self) -> None:
        tag = self._tag()
        self._vincular(tag.tagId)

        tag_service.set_tag_ativo(self.db, tag.tagId, False, 1)
        self.db.expire_all()
        lead = oportunidade_service.get_oportunidade(self.db, 10, 1)
        self.assertEqual(OportunidadeResponse.model_validate(lead).tags, [])

        tag_service.set_tag_ativo(self.db, tag.tagId, True, 1)
        self.db.expire_all()
        lead = oportunidade_service.get_oportunidade(self.db, 10, 1)
        self.assertEqual(len(OportunidadeResponse.model_validate(lead).tags), 1)

    def test_editar_selecao_nao_perde_vinculo_de_tag_inativa(self) -> None:
        inativa = self._tag("Antiga")
        ativa = self._tag("VIP")
        self._vincular(inativa.tagId)
        tag_service.set_tag_ativo(self.db, inativa.tagId, False, 1)

        self._vincular(ativa.tagId)

        tag_service.set_tag_ativo(self.db, inativa.tagId, True, 1)
        self.db.expire_all()
        lead = oportunidade_service.get_oportunidade(self.db, 10, 1)
        nomes = [t.tagNome for t in OportunidadeResponse.model_validate(lead).tags]
        self.assertEqual(nomes, ["Antiga", "VIP"])

    def test_lead_de_outra_empresa_nao_e_encontrado(self) -> None:
        tag = self._tag("VIP", empresa=2)
        with self.assertRaises(HTTPException) as erro:
            oportunidade_service.set_tags(
                self.db, 10, OportunidadeTagsRequest(tagIds=[tag.tagId]), 2
            )
        self.assertEqual(erro.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
