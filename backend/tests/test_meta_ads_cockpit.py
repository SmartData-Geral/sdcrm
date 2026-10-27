import json
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import get_current_user
from backend.database import get_db
from backend.exceptions import BadRequestError
from backend.models.etapa_kanban import EtapaKanban
from backend.routers import meta_ads_router
from backend.services.meta_ads import cockpit as ck
from backend.services.meta_ads import indicadores as ind
from backend.tests import banco_sqlite as b

NOME_LEAD = "Fulana Revisora"
TELEFONE_LEAD = "11987654321"
EMAIL_LEAD = "fulana.revisora@exemplo.com.br"


class BaseCockpit(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.emp_id = self.emp.empId
        # As etapas de MQL e oportunidade precisam existir antes da config ser criada (achadas por nome).
        for ordem, nome in [(3, "Reunião de Levantamento"), (4, "Reunião de Vendas")]:
            self.db.add(EtapaKanban(etkEmpId=self.emp_id, etkNome=nome, etkOrdem=ordem))
        self.db.commit()
        self.anuncios = b.criar_origem(self.db, self.emp_id, "Anúncios")
        self.conta = b.criar_conta(self.db, self.emp_id, origens=[self.anuncios.ccoId])
        self.conta.macExigirRastreio = True
        self.db.commit()
        self.c1 = b.criar_campanha(self.db, self.conta, "1", "Campanha 1")
        self.s1 = b.criar_conjunto(self.db, self.c1, "11", "Conjunto 1")
        self.a1 = b.criar_anuncio(self.db, self.s1, "111", "Anúncio A")
        self.a2 = b.criar_anuncio(self.db, self.s1, "112", "Anúncio B", status="PAUSED")
        self.a3 = b.criar_anuncio(self.db, self.s1, "113", "Anúncio C sem gasto")

        # Dados de agosto a outubro (campanha e anuncios)
        b.criar_insight(self.db, self.c1, date(2026, 8, 20), 80, leads=1)
        b.criar_insight(self.db, self.c1, date(2026, 9, 10), 120, leads=2)
        b.criar_insight(self.db, self.c1, date(2026, 10, 5), 150, leads=10)
        b.criar_insight(self.db, self.c1, date(2026, 10, 6), 200)
        b.criar_insight_anuncio(self.db, self.a1, date(2026, 10, 5), 150, leads=10)
        b.criar_insight_anuncio(self.db, self.a2, date(2026, 10, 6), 200)  # pausado, gasto sem lead

        cco = self.anuncios.ccoId
        # Setembro: dois leads na campanha
        for dia in (date(2026, 9, 12), date(2026, 9, 14)):
            b.criar_oportunidade(self.db, self.emp_id, opoCcoId=cco, opoMcgId=self.c1.mcgId,
                                 opoManId=self.a1.manId, opoMetaAnuncioId="111", opoDataRecebimento=dia)
        # Outubro: 36 leads no CRM, 3 viram MQL (ganhos)
        for i in range(36):
            extra = {}
            if i < 3:
                extra = dict(opoStatusFechamento="ganho", opoDataFechamento=date(2026, 10, 20),
                             opoValorFechado=1000, opoFechadoRecorrencia=0)
            b.criar_oportunidade(self.db, self.emp_id, opoCcoId=cco, opoMcgId=self.c1.mcgId,
                                 opoManId=self.a1.manId, opoMetaAnuncioId="111",
                                 opoDataRecebimento=date(2026, 10, 1 + i % 28), **extra)
        # Lead de origem Meta sem sinal da Meta: vai para a revisao de origem
        b.criar_oportunidade(
            self.db, self.emp_id, opoCcoId=cco, opoNomeContato=NOME_LEAD, opoTelefone=TELEFONE_LEAD,
            opoEmail=EMAIL_LEAD, opoDataRecebimento=date(2026, 10, 9),
        )

    def filtro(self, ini=date(2026, 10, 1), fim=date(2026, 10, 31), **kw) -> ind.FiltroPainel:
        return ind.FiltroPainel(ini, fim, **kw)

    def montar(self, **kw):
        return ck.montar(self.db, self.emp_id, self.filtro(**kw))


class ServicoTests(BaseCockpit):
    def test_exige_datas(self) -> None:
        with self.assertRaises(BadRequestError):
            ck.montar(self.db, self.emp_id, ind.FiltroPainel(None, None))

    def test_total_bate_com_painel(self) -> None:
        resposta = self.montar()
        painel = ind.painel(self.db, self.emp_id, self.filtro())
        self.assertEqual(resposta.total, painel.total)
        self.assertEqual(resposta.total.filhos, [])
        self.assertEqual(resposta.total.leadsCrm, 36)

    def test_anterior_e_variacao(self) -> None:
        resposta = self.montar()
        self.assertEqual((resposta.anteriorInicio, resposta.anteriorFim), (date(2026, 8, 31), date(2026, 9, 30)))
        setembro = ind.painel(self.db, self.emp_id, self.filtro(date(2026, 8, 31), date(2026, 9, 30)))
        self.assertEqual(resposta.anterior, setembro.total)
        self.assertEqual((resposta.anterior.investimento, resposta.anterior.leadsCrm), (120, 2))
        self.assertTrue(resposta.anteriorTemDados)

    def test_anterior_sem_dados(self) -> None:
        resposta = self.montar(ini=date(2026, 1, 1), fim=date(2026, 10, 27))
        self.assertFalse(resposta.anteriorTemDados)

    def test_serie_aparada(self) -> None:
        resposta = self.montar(ini=date(2026, 1, 1), fim=date(2026, 12, 31))
        self.assertEqual(resposta.intervalo, "mes")
        self.assertEqual([p.rotulo for p in resposta.serie], ["ago/2026", "set/2026", "out/2026"])
        total = resposta.total
        self.assertEqual(sum(p.investimento for p in resposta.serie), total.investimento)
        self.assertEqual(sum(p.leadsCrm for p in resposta.serie), total.leadsCrm)
        agosto = resposta.serie[0]
        self.assertEqual((agosto.investimento, agosto.leadsMeta, agosto.cpl), (80, 1, 80.0))

    def test_serie_semanal_para_periodo_curto(self) -> None:
        resposta = self.montar(ini=date(2026, 10, 1), fim=date(2026, 10, 31))
        self.assertEqual(resposta.intervalo, "semana")
        self.assertEqual(resposta.serie[0].inicio, date(2026, 10, 1))
        self.assertIsNone(next(p for p in resposta.serie if p.leadsMeta == 0).cpl)

    def test_criativos_e_pausado(self) -> None:
        resposta = self.montar()
        nomes = [c.nome for c in resposta.criativos]
        self.assertEqual(nomes, ["Anúncio B", "Anúncio A"])  # so com investimento, maior primeiro
        pausado, ativo = resposta.criativos
        self.assertFalse(pausado.ativo)
        self.assertEqual(pausado.quadrante, "pausar")
        self.assertEqual(pausado.recomendacao, "Manter pausado")
        self.assertEqual(pausado.campanha, "Campanha 1")
        self.assertTrue(ativo.ativo)
        self.assertEqual(ativo.leadsCrm, 36)

    def test_funil_e_gargalo(self) -> None:
        resposta = self.montar()
        self.assertEqual((resposta.total.leadsCrm, resposta.total.mqls), (36, 3))
        self.assertEqual(resposta.gargalo, "mql")
        self.assertEqual(resposta.fraseGargalo, "Para cada 12 leads no CRM, só 1 vira MQL.")
        etapas = {e.chave: e for e in resposta.funil}
        self.assertEqual(list(etapas), ["impressoes", "cliques", "leads", "crm", "mql", "oportunidade", "contrato"])
        self.assertTrue(etapas["mql"].gargalo)
        self.assertFalse(etapas["crm"].gargalo)
        self.assertIsNone(etapas["impressoes"].taxa)
        self.assertEqual(etapas["mql"].taxa, 8.33)
        self.assertEqual(etapas["crm"].taxa, round(36 / 10 * 100, 2))  # leads CRM contra leads Meta
        self.assertEqual(etapas["mql"].custo, resposta.total.custoMql)
        self.assertEqual(resposta.taxaMql, 8.33)

    def test_selos_e_metas(self) -> None:
        resposta = self.montar()
        self.assertEqual(resposta.metas.cpl, 150)
        self.assertEqual(resposta.metas.custoMqlImplicito, 1500)
        # CPL 35 (350 / 10): bom; taxa 8,33% de meta 10%: atencao
        self.assertEqual(resposta.selos.cpl, "bom")
        self.assertEqual(resposta.selos.taxaMql, "atencao")
        self.assertEqual(resposta.selos.saude, "atencao")

    def test_sem_dados_pessoais(self) -> None:
        resposta = self.montar()
        texto = json.dumps(resposta.model_dump(mode="json"), ensure_ascii=False)
        for dado in (NOME_LEAD, TELEFONE_LEAD, EMAIL_LEAD):
            self.assertNotIn(dado, texto)
        self.assertEqual(resposta.operacao.origemRevisar, 1)
        self.assertEqual(resposta.operacao.alertasAbertos, 0)


class RotaTests(BaseCockpit):
    def setUp(self) -> None:
        super().setUp()
        app = FastAPI()
        app.include_router(meta_ads_router.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(usuId=1, usuAdmin=False)
        self.http = TestClient(app)
        self.h = {"X-Company-Id": str(self.emp_id)}

    def test_rota_exige_datas(self) -> None:
        with patch.object(meta_ads_router, "require_user_in_company"):
            self.assertEqual(self.http.get("/api/meta-ads/cockpit", headers=self.h).status_code, 422)
            resp = self.http.get(
                "/api/meta-ads/cockpit?data_inicial=2026-10-01&data_final=2026-10-31", headers=self.h
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        corpo = resp.json()
        self.assertEqual(corpo["gargalo"], "mql")
        self.assertEqual(corpo["anteriorInicio"], "2026-08-31")


if __name__ == "__main__":
    unittest.main()
