import unittest
from datetime import datetime, timezone

from sqlalchemy import select

from backend.models.etapa_kanban import EtapaKanban
from backend.models.oportunidade_etapa_historico import OportunidadeEtapaHistorico as Oeh
from backend.models.oportunidade_historico import OportunidadeHistorico
from backend.schemas.oportunidade import (
    OportunidadeCreate,
    OportunidadeMoverEtapaRequest,
    OportunidadeUpdate,
)
from backend.services import etapa_historico, oportunidade_service
from backend.tests.banco_sqlite import criar_empresa, criar_oportunidade, nova_sessao


def etapa(db, emp_id, nome, pipeline="leads"):
    e = EtapaKanban(etkEmpId=emp_id, etkNome=nome, etkPipeline=pipeline)
    db.add(e)
    db.commit()
    return e


def linhas(db):
    return [
        (r.oehEtkIdDe, r.oehEtkIdPara, r.oehOrigem)
        for r in db.scalars(select(Oeh).order_by(Oeh.oehId))
    ]


class BaseTeste(unittest.TestCase):
    def setUp(self) -> None:
        self.db = nova_sessao()
        self.emp = criar_empresa(self.db)
        self.a = etapa(self.db, self.emp.empId, "Contatos")
        self.b = etapa(self.db, self.emp.empId, "Reunião de Levantamento")


class RegistroTests(BaseTeste):
    def test_mover_etapa_grava_transicao(self) -> None:
        opo = criar_oportunidade(self.db, self.emp.empId, opoEtkId=self.a.etkId)
        oportunidade_service.mover_etapa(
            self.db, opo.opoId, OportunidadeMoverEtapaRequest(opoEtkId=self.b.etkId), self.emp.empId
        )
        self.assertEqual(linhas(self.db), [(self.a.etkId, self.b.etkId, "ui")])

    def test_mover_etapa_origem_mcp(self) -> None:
        opo = criar_oportunidade(self.db, self.emp.empId, opoEtkId=self.a.etkId)
        oportunidade_service.mover_etapa(
            self.db, opo.opoId, OportunidadeMoverEtapaRequest(opoEtkId=self.b.etkId),
            self.emp.empId, origem="mcp",
        )
        self.assertEqual(linhas(self.db)[0][2], "mcp")

    def test_mesma_etapa_nao_grava(self) -> None:
        opo = criar_oportunidade(self.db, self.emp.empId, opoEtkId=self.a.etkId)
        oportunidade_service.mover_etapa(
            self.db, opo.opoId, OportunidadeMoverEtapaRequest(opoEtkId=self.a.etkId), self.emp.empId
        )
        self.assertEqual(linhas(self.db), [])

    def test_criacao_grava_estagio_inicial(self) -> None:
        oportunidade_service.create_oportunidade(
            self.db, OportunidadeCreate(opoTitulo="X", opoEtkId=self.a.etkId), self.emp.empId
        )
        self.assertEqual(linhas(self.db), [(None, self.a.etkId, "ui")])

    def test_update_com_troca_de_etapa_grava(self) -> None:
        opo = criar_oportunidade(self.db, self.emp.empId, opoEtkId=self.a.etkId)
        oportunidade_service.update_oportunidade(
            self.db, opo.opoId, OportunidadeUpdate(opoEtkId=self.b.etkId), self.emp.empId
        )
        self.assertEqual(linhas(self.db), [(self.a.etkId, self.b.etkId, "ui")])

    def test_update_sem_troca_de_etapa_nao_grava(self) -> None:
        opo = criar_oportunidade(self.db, self.emp.empId, opoEtkId=self.a.etkId)
        oportunidade_service.update_oportunidade(
            self.db, opo.opoId, OportunidadeUpdate(opoTitulo="Novo"), self.emp.empId
        )
        self.assertEqual(linhas(self.db), [])


class CargaRetroativaTests(BaseTeste):
    def _opo_com_texto(self, texto, quando=datetime(2026, 10, 10, 14, 0, tzinfo=timezone.utc)):
        opo = criar_oportunidade(self.db, self.emp.empId, opoEtkId=self.b.etkId)
        self.db.add(
            OportunidadeHistorico(
                ophEmpId=self.emp.empId, ophOpoId=opo.opoId, ophDataRegistro=quando,
                ophConteudo=texto,
            )
        )
        self.db.commit()
        return opo

    def test_carga_retroativa_le_texto_do_historico(self) -> None:
        opo = self._opo_com_texto(
            'Etapa alterada de " contatos " para "Reunião de Levantamento".'
        )
        r = etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=True)
        self.assertEqual(r, {"transicoes": 1, "criacoes": 1, "nao_casadas": 0})
        rows = self.db.scalars(select(Oeh).order_by(Oeh.oehId)).all()
        trans = [x for x in rows if x.oehEtkIdDe is not None][0]
        self.assertEqual((trans.oehEtkIdDe, trans.oehEtkIdPara), (self.a.etkId, self.b.etkId))
        self.assertEqual(trans.oehData.replace(tzinfo=None), datetime(2026, 10, 10, 14, 0))
        self.assertEqual(trans.oehOrigem, "retroativo")
        criacao = [x for x in rows if x.oehEtkIdDe is None][0]
        self.assertEqual(criacao.oehEtkIdPara, self.a.etkId)
        self.assertEqual(
            criacao.oehData.replace(tzinfo=None), opo.opoDataCriacao.replace(tzinfo=None)
        )

    def test_carga_retroativa_nome_desconhecido_conta_nao_casada(self) -> None:
        self._opo_com_texto('Etapa alterada de "Inexistente" para "Contatos".')
        r = etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=True)
        self.assertEqual(r["nao_casadas"], 1)
        self.assertEqual(r["transicoes"], 0)

    def test_carga_retroativa_idempotente(self) -> None:
        self._opo_com_texto('Etapa alterada de "Contatos" para "Reunião de Levantamento".')
        etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=True)
        antes = len(linhas(self.db))
        etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=True)
        self.assertEqual(len(linhas(self.db)), antes)

    def test_simulacao_nao_grava(self) -> None:
        self._opo_com_texto('Etapa alterada de "Contatos" para "Reunião de Levantamento".')
        r = etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=False)
        self.assertEqual(r["transicoes"], 1)
        self.assertEqual(linhas(self.db), [])


if __name__ == "__main__":
    unittest.main()
