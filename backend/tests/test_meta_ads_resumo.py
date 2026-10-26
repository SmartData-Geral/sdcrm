import json
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.auth import get_current_user
from backend.database import get_db
from backend.models.meta_ads_alerta import MetaAdsAlerta
from backend.models.meta_ads_resumo import MetaAdsResumo
from backend.routers import meta_ads_router
from backend.schemas.meta_ads import MetaAdsLinha
from backend.services.meta_ads import resumo as r
from backend.services.meta_ads.config_monitor import obter_config
from backend.tests import banco_sqlite as b

SEGUNDA = date(2026, 10, 26)
TERCA = date(2026, 10, 27)


def hora_sp(ano, mes, dia, h, m=0, s=0, us=0):
    """Instante com fuso: horario de Sao Paulo (UTC-3 em outubro de 2026)."""
    return datetime(ano, mes, dia, h + 3, m, s, us, tzinfo=timezone.utc)


def linha(id_, invest, *, leads=0, leads_crm=0, mqls=0, custo_mql=None, cpl=None, nome=None):
    return MetaAdsLinha(
        nivel="anuncio", id=id_, mcgId=1, nome=nome or f"A{id_}", status="ACTIVE", macId=1,
        investimento=invest, impressoes=0, cliques=0, leadsMeta=leads, leadsCrm=leads_crm,
        mqls=mqls, oportunidades=0, vendas=0, mrr=0, projeto=0, ctr=None, cpc=None, cpl=cpl,
        custoLeadCrm=None, custoMql=custo_mql, custoOportunidade=None, cac=None, retorno=None,
        horasPrimeiroContato=None,
    )


class ProvedorFalso:
    def __init__(self, texto="Leitura de teste.", erro=None):
        self.texto, self.erro, self.chamadas = texto, erro, []

    def chat_completion(self, messages, *, temperature):
        self.chamadas.append((messages, temperature))
        if self.erro:
            raise self.erro
        return self.texto


class PuroTests(unittest.TestCase):
    def test_periodo_anterior(self) -> None:
        self.assertEqual(r.periodo_anterior(date(2026, 10, 26)), (date(2026, 10, 23), date(2026, 10, 25)))
        self.assertEqual(r.periodo_anterior(date(2026, 10, 27)), (date(2026, 10, 26), date(2026, 10, 26)))

    def test_ranking_regras(self) -> None:
        mql_barato = linha(1, 100, leads=4, mqls=2, custo_mql=50, cpl=25)
        mql_caro = linha(2, 200, leads=4, mqls=1, custo_mql=200, cpl=50)
        lead_barato = linha(3, 60, leads=3, cpl=20)
        lead_caro = linha(4, 300, leads=2, cpl=150)
        lead_medio = linha(5, 100, leads=2, cpl=50)
        sem_lead_alto = linha(6, 500)
        sem_lead_baixo = linha(7, 80)
        abaixo_do_minimo = linha(8, 10)  # sem lead, mas gasto < minimo
        todos = [
            mql_barato, mql_caro, lead_barato, lead_caro, lead_medio,
            sem_lead_alto, sem_lead_baixo, abaixo_do_minimo,
        ]
        melhores, piores = r.ranking(todos, 50)
        self.assertEqual([a.id for a in melhores], [1, 2, 3])
        self.assertEqual([a.id for a in piores], [6, 7, 4])
        self.assertFalse({a.id for a in melhores} & {a.id for a in piores})
        self.assertNotIn(8, {a.id for a in melhores + piores})

    def test_ranking_poucos_anuncios_nao_repete(self) -> None:
        unico = linha(1, 100, leads=2, cpl=50)
        melhores, piores = r.ranking([unico], 50)
        self.assertEqual(([a.id for a in melhores], piores), ([1], []))
        self.assertEqual(r.ranking([], 50), ([], []))


class BaseResumo(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.e = self.emp.empId
        self.origem = b.criar_origem(self.db, self.e, "Anúncios")
        self.conta = b.criar_conta(self.db, self.e, origens=[self.origem.ccoId])
        self.camp = b.criar_campanha(self.db, self.conta, "c1", "Campanha Alfa")
        self.conj = b.criar_conjunto(self.db, self.camp, "s1", "Conjunto 1")
        self.anu = b.criar_anuncio(self.db, self.conj, "a1", "Anúncio Beta")
        # Segunda 26/10: periodo anterior 23-25/10, ultimos 7 dias 19-25/10.
        b.criar_insight(self.db, self.camp, date(2026, 10, 24), 120, leads=3)
        b.criar_insight_anuncio(self.db, self.anu, date(2026, 10, 24), 120, leads=3)
        b.criar_insight(self.db, self.camp, date(2026, 10, 20), 60, leads=1)
        b.criar_insight_anuncio(self.db, self.anu, date(2026, 10, 20), 60, leads=1)
        b.criar_oportunidade(
            self.db, self.e, opoCcoId=self.origem.ccoId, opoMcgId=self.camp.mcgId,
            opoManId=self.anu.manId, opoMetaAnuncioId="a1", opoDataRecebimento=date(2026, 10, 24),
            opoNomeContato="Fulana Pessoal da Silva", opoEmail="fulana.pessoal@exemplo.com",
            opoTelefone="+5511987654321",
        )
        self.cfg = obter_config(self.db, self.e)
        self.cfg.mmcGastoMinRanking = 50
        self.db.commit()
        self.db.add(
            MetaAdsAlerta(
                malEmpId=self.e, malTipo="sem_contato", malChave="lead:1", malStatus="aberto",
                malMensagem="Fulana Pessoal da Silva sem contato", malDados={"nome": "Fulana Pessoal da Silva"},
                malPrimeiroEm=datetime(2026, 10, 25), malUltimoEm=datetime(2026, 10, 25),
            )
        )
        self.db.commit()

    def _resumos(self):
        return list(self.db.execute(select(MetaAdsResumo).where(MetaAdsResumo.mrsEmpId == self.e)).scalars())


class DadosTests(BaseResumo):
    def test_estrutura_e_numeros(self) -> None:
        d = r.montar_dados(self.db, self.e, SEGUNDA)
        self.assertEqual(
            set(d),
            {"periodo", "ultimos7", "comparacao", "campanhas", "anuncios", "melhores", "piores",
             "cobertura", "horasPrimeiroContato", "alertasAbertos"},
        )
        self.assertEqual((d["periodo"]["inicio"], d["periodo"]["fim"], d["periodo"]["dias"]), ("2026-10-23", "2026-10-25", 3))
        self.assertEqual(d["periodo"]["investimento"], 120.0)
        self.assertEqual(d["ultimos7"]["investimento"], 180.0)
        self.assertEqual(d["comparacao"]["mediaDiariaPeriodo"]["investimento"], 40.0)
        self.assertEqual(d["comparacao"]["mediaDiariaUltimos7"]["investimento"], round(180 / 7, 2))
        self.assertEqual([a["nome"] for a in d["anuncios"]], ["Anúncio Beta"])
        self.assertEqual([a["nome"] for a in d["melhores"]], ["Anúncio Beta"])
        self.assertEqual(d["campanhas"][0]["nome"], "Campanha Alfa")
        self.assertEqual(d["alertasAbertos"], 1)

    def test_dados_sem_dados_pessoais(self) -> None:
        texto = json.dumps(r.montar_dados(self.db, self.e, SEGUNDA), ensure_ascii=False)
        for pessoal in ("Fulana", "Pessoal", "fulana.pessoal", "exemplo.com", "987654321", "revisaoOrigem"):
            self.assertNotIn(pessoal, texto)


class LeituraTests(BaseResumo):
    def test_leitura_ok_recebe_so_dados(self) -> None:
        prov = ProvedorFalso("Gasto subiu.")
        res = r.gerar(self.db, self.e, SEGUNDA, provedor=prov)
        self.assertEqual((res.mrsLeitura, res.mrsAviso), ("Gasto subiu.", None))
        mensagens, temperatura = prov.chamadas[0]
        self.assertEqual(temperatura, 0.3)
        self.assertEqual(mensagens[0]["role"], "system")
        self.assertTrue(mensagens[0]["content"].startswith("Você é um analista de mídia paga."))
        self.assertNotIn("Fulana", json.dumps(mensagens, ensure_ascii=False))

    def test_leitura_falha_vira_aviso(self) -> None:
        res = r.gerar(self.db, self.e, SEGUNDA, provedor=ProvedorFalso(erro=RuntimeError("timeout")))
        self.assertIsNone(res.mrsLeitura)
        self.assertTrue(res.mrsAviso.startswith("Leitura por IA indisponível"))
        self.assertIn("timeout", res.mrsAviso)
        self.assertEqual(len(self._resumos()), 1)  # o resumo sai mesmo sem a leitura

    def test_sem_chave_vira_aviso(self) -> None:
        with patch("backend.services.llm.llm_factory.settings") as cfg:
            cfg.LLM_PROVIDER = "openai"
            cfg.LLM_OPENAI_API_KEY = ""
            leitura, aviso = r.gerar_leitura({"a": 1})
        self.assertIsNone(leitura)
        self.assertTrue(aviso.startswith("Leitura por IA indisponível"))

    def test_regerar_substitui(self) -> None:
        r.gerar(self.db, self.e, SEGUNDA, provedor=ProvedorFalso("primeira"))
        res = r.gerar(self.db, self.e, SEGUNDA, provedor=ProvedorFalso("segunda"))
        linhas = self._resumos()
        self.assertEqual(len(linhas), 1)
        self.assertEqual((linhas[0].mrsLeitura, res.mrsLeitura), ("segunda", "segunda"))
        self.assertEqual((linhas[0].mrsInicio, linhas[0].mrsFim), (date(2026, 10, 23), date(2026, 10, 25)))


class DevidoTests(BaseResumo):
    def _devido(self, agora):
        return r.gerar_se_devido(self.db, self.e, agora, provedor=ProvedorFalso())

    def test_gerar_se_devido(self) -> None:
        self.assertFalse(self._devido(hora_sp(2026, 10, 24, 9)))  # sabado
        self.assertFalse(self._devido(hora_sp(2026, 10, 25, 9)))  # domingo
        self.assertFalse(self._devido(hora_sp(2026, 10, 26, 7, 59)))  # antes (fora da tolerancia)
        self.assertEqual(self._resumos(), [])
        self.assertTrue(self._devido(hora_sp(2026, 10, 26, 8)))
        self.assertFalse(self._devido(hora_sp(2026, 10, 26, 9)))  # ja gerado hoje
        self.assertEqual(len(self._resumos()), 1)

    def test_tolera_timer_alguns_ms_antes_da_hora(self) -> None:
        self.assertTrue(self._devido(hora_sp(2026, 10, 26, 7, 59, 59, 980000)))
        self.assertEqual(self._resumos()[0].mrsData, SEGUNDA)

    def test_naive_e_utc(self) -> None:
        self.assertTrue(self._devido(datetime(2026, 10, 26, 11, 0)))  # 08:00 em SP

    def test_hora_configurada(self) -> None:
        self.cfg.mmcHoraResumo = 10
        self.db.commit()
        self.assertFalse(self._devido(hora_sp(2026, 10, 26, 9)))
        self.assertTrue(self._devido(hora_sp(2026, 10, 26, 10)))

    def test_sem_conta_ativa_nao_gera(self) -> None:
        self.conta.macAtivo = False
        self.db.commit()
        self.assertFalse(self._devido(hora_sp(2026, 10, 26, 9)))
        self.assertEqual(self._resumos(), [])


class RotasTests(BaseResumo):
    def setUp(self) -> None:
        super().setUp()
        app = FastAPI()
        app.include_router(meta_ads_router.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(usuId=1, usuAdmin=False)
        self.http = TestClient(app)
        self.h = {"X-Company-Id": str(self.e)}

    def test_rotas(self) -> None:
        with patch.object(meta_ads_router, "require_user_in_company") as exigir, patch.object(
            r, "get_scope_provider", create=True
        ), patch(
            "backend.services.llm.llm_factory.get_scope_provider", return_value=ProvedorFalso("ok")
        ):
            self.assertEqual(self.http.get("/api/meta-ads/resumos/ultimo", headers=self.h).status_code, 404)
            self.assertEqual(self.http.get("/api/meta-ads/resumos/2026-10-26", headers=self.h).status_code, 404)
            self.assertEqual(self.http.get("/api/meta-ads/resumos", headers=self.h).json(), {"items": []})
            resp = self.http.post("/api/meta-ads/resumos/2026-10-26/gerar", headers=self.h)
            self.assertEqual(resp.status_code, 200, resp.text)
            self.assertEqual(resp.json()["mrsLeitura"], "ok")
            self.http.post("/api/meta-ads/resumos/2026-10-27/gerar", headers=self.h)
            lista = self.http.get("/api/meta-ads/resumos?limite=1", headers=self.h).json()["items"]
            self.assertEqual([i["mrsData"] for i in lista], ["2026-10-27"])
            ultimo = self.http.get("/api/meta-ads/resumos/ultimo", headers=self.h).json()
            self.assertEqual(ultimo["mrsData"], "2026-10-27")
            dia = self.http.get("/api/meta-ads/resumos/2026-10-26", headers=self.h).json()
            self.assertEqual(dia["mrsFim"], "2026-10-25")
            self.assertEqual(self.http.get("/api/meta-ads/resumos/xx", headers=self.h).status_code, 400)
            self.assertEqual(self.http.post("/api/meta-ads/resumos/ultimo/gerar", headers=self.h).status_code, 400)
        self.assertTrue(exigir.called)


if __name__ == "__main__":
    unittest.main()
