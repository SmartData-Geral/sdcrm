import contextlib
import io
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

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


def etapa(db, emp_id, nome, pipeline="leads", ordem=0, ativo=True):
    e = EtapaKanban(etkEmpId=emp_id, etkNome=nome, etkPipeline=pipeline, etkOrdem=ordem, etkAtivo=ativo)
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
        self.a = etapa(self.db, self.emp.empId, "Contatos", ordem=1)
        self.b = etapa(self.db, self.emp.empId, "Reunião de Levantamento", ordem=3)


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


class IntakeOrigemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = nova_sessao()
        self.emp = criar_empresa(self.db)
        self.contatos = etapa(self.db, self.emp.empId, "Contatos", pipeline="default", ordem=1)

    def _criar(self, email, **kw):
        from backend.schemas.lead_integracao import LeadIntakeRequest
        from backend.services import lead_intake_service
        from backend.services.lead_normalizacao import normalizar_email, variantes_telefone

        payload = LeadIntakeRequest(source="mcp", email=email, name="Ana")
        return lead_intake_service._processar_com_lock(
            self.db, emp_id=self.emp.empId, ich_id=None, payload=payload,
            email_norm=normalizar_email(email), fone_norm=None, fones=variantes_telefone(None), **kw,
        )

    def test_lead_criado_pelo_mcp_grava_origem_mcp(self) -> None:
        self._criar("a@b.com", origem_etapa="mcp")
        self.assertEqual(linhas(self.db), [(None, self.contatos.etkId, "mcp")])

    def test_api_de_leads_continua_api(self) -> None:
        self._criar("c@d.com")
        self.assertEqual(linhas(self.db), [(None, self.contatos.etkId, "api")])


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
        self.assertEqual(
            r, {"transicoes": 1, "criacoes": 1, "nao_casadas": 0, "sem_texto_fora_do_inicial": 0}
        )
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

    def test_nao_duplica_transicao_ao_vivo(self) -> None:
        criada = oportunidade_service.create_oportunidade(
            self.db, OportunidadeCreate(opoTitulo="X", opoEtkId=self.a.etkId), self.emp.empId
        )
        oportunidade_service.mover_etapa(
            self.db, criada.opoId, OportunidadeMoverEtapaRequest(opoEtkId=self.b.etkId),
            self.emp.empId,
        )
        antes = linhas(self.db)
        r = etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=True)
        self.assertEqual(
            r, {"transicoes": 0, "criacoes": 0, "nao_casadas": 0, "sem_texto_fora_do_inicial": 0}
        )
        self.assertEqual(linhas(self.db), antes)

    def test_importa_texto_anterior_a_primeira_linha_ao_vivo(self) -> None:
        opo = self._opo_com_texto('Etapa alterada de "Contatos" para "Reunião de Levantamento".')
        etapa_historico.registrar_transicao(
            self.db, opo, self.b.etkId, self.a.etkId, "ui",
            datetime(2026, 10, 20, tzinfo=timezone.utc),
        )
        self.db.commit()
        r = etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=True)
        self.assertEqual(r["transicoes"], 1)
        self.assertEqual(r["criacoes"], 1)

    def test_sem_texto_no_estagio_inicial_grava_criacao(self) -> None:
        etapa(self.db, self.emp.empId, "Inativa antes", ordem=0, ativo=False)  # inativa nao conta
        etapa(self.db, self.emp.empId, "Outro pipeline", pipeline="vendas", ordem=0)
        opo = criar_oportunidade(self.db, self.emp.empId, opoEtkId=self.a.etkId)
        r = etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=True)
        self.assertEqual((r["criacoes"], r["sem_texto_fora_do_inicial"]), (1, 0))
        rows = self.db.scalars(select(Oeh)).all()
        self.assertEqual([(x.oehEtkIdDe, x.oehEtkIdPara, x.oehOrigem) for x in rows], [(None, self.a.etkId, "retroativo")])
        self.assertEqual(rows[0].oehData.replace(tzinfo=None), opo.opoDataCriacao.replace(tzinfo=None))

    def test_sem_texto_fora_do_estagio_inicial_nao_grava_e_conta(self) -> None:
        vendas = etapa(self.db, self.emp.empId, "Reunião de Vendas", ordem=4)
        criar_oportunidade(self.db, self.emp.empId, opoEtkId=vendas.etkId)
        r = etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=False)
        self.assertEqual((r["criacoes"], r["sem_texto_fora_do_inicial"]), (0, 1))  # simulacao mostra
        r = etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=True)
        self.assertEqual((r["criacoes"], r["sem_texto_fora_do_inicial"]), (0, 1))
        self.assertEqual(linhas(self.db), [])

    def test_com_texto_criacao_usa_estagio_de_origem_mesmo_fora_do_inicial(self) -> None:
        # Regra inalterada quando ha texto: a criacao usa o "de" da transicao mais antiga.
        opo = self._opo_com_texto('Etapa alterada de "Reunião de Levantamento" para "Contatos".')
        opo.opoEtkId = self.a.etkId
        self.db.commit()
        r = etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=True)
        self.assertEqual((r["criacoes"], r["sem_texto_fora_do_inicial"]), (1, 0))
        criacao = [x for x in self.db.scalars(select(Oeh)) if x.oehEtkIdDe is None][0]
        self.assertEqual(criacao.oehEtkIdPara, self.b.etkId)

    def test_simulacao_nao_grava(self) -> None:
        self._opo_com_texto('Etapa alterada de "Contatos" para "Reunião de Levantamento".')
        r = etapa_historico.carga_retroativa(self.db, self.emp.empId, aplicar=False)
        self.assertEqual(r["transicoes"], 1)
        self.assertEqual(linhas(self.db), [])


class ScriptCargaTests(BaseTeste):
    def test_saida_mostra_os_sem_texto_fora_do_inicial(self) -> None:
        from backend.scripts import carga_etapas

        vendas = etapa(self.db, self.emp.empId, "Reunião de Vendas", ordem=4)
        criar_oportunidade(self.db, self.emp.empId, opoEtkId=vendas.etkId)
        saida = io.StringIO()
        with patch.object(carga_etapas, "SessionLocal", return_value=contextlib.nullcontext(self.db)),              contextlib.redirect_stdout(saida):
            r = carga_etapas.main(["--empresa", str(self.emp.empId)])
        self.assertEqual(r["sem_texto_fora_do_inicial"], 1)
        self.assertIn("SIMULACAO", saida.getvalue())
        self.assertIn("1 oportunidade(s) sem texto de mudança de etapa e fora do estágio inicial", saida.getvalue())
        self.assertEqual(linhas(self.db), [])


if __name__ == "__main__":
    unittest.main()
