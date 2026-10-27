import json
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.auth import get_current_user
from backend.database import get_db
from backend.routers import meta_ads_router

from backend.models.meta_ads_cockpit_leitura import MetaAdsCockpitLeitura
from backend.schemas.meta_ads import MetaAdsMonitorConfigUpdate
from backend.services.meta_ads import cockpit as ck
from backend.services.meta_ads import cockpit_ia as ia
from backend.services.meta_ads.config_monitor import atualizar_config
from backend.services.meta_ads.resumo import PREFIXO_AVISO
from backend.tests import banco_sqlite as b
from backend.tests.test_meta_ads_cockpit import EMAIL_LEAD, NOME_LEAD, TELEFONE_LEAD, BaseCockpit
from backend.tests.test_meta_ads_resumo import ProvedorFalso

FABRICA = "backend.services.llm.llm_factory.get_scope_provider"
LEITURA = {
    "manchete": "O custo por lead está bom, mas poucos viram MQL.",
    "funciona": "O anúncio A traz leads baratos.",
    "problema": "Só 8% dos leads viram MQL.",
    "olharAgora": "Verifique a qualificação dos leads.",
}


def provedor_ok() -> ProvedorFalso:
    return ProvedorFalso(json.dumps(LEITURA, ensure_ascii=False))


class ContextoTests(BaseCockpit):
    def test_contexto_sem_dados_pessoais(self) -> None:
        for i in range(31):
            anuncio = b.criar_anuncio(self.db, self.s1, f"9{i:02d}", f"Extra {i}")
            b.criar_insight_anuncio(self.db, anuncio, date(2026, 10, 7), 10 + i)
        contexto = ia.contexto_ia(self.montar())
        texto = json.dumps(contexto, ensure_ascii=False)
        for dado in (NOME_LEAD, TELEFONE_LEAD, EMAIL_LEAD, "revisaoOrigem"):
            self.assertNotIn(dado, texto)
        self.assertEqual(
            set(contexto),
            {"periodo", "metas", "total", "anterior", "anteriorTemDados", "taxaMql", "selos", "funil",
             "gargalo", "fraseGargalo", "intervalo", "serie", "criativos", "operacao"},
        )
        self.assertEqual(len(contexto["criativos"]), 30)
        investimentos = [c["investimento"] for c in contexto["criativos"]]
        self.assertEqual(investimentos, sorted(investimentos, reverse=True))
        for chave in ("filhos", "id", "nivel"):
            self.assertNotIn(chave, contexto["total"])
            self.assertNotIn(chave, contexto["anterior"])

    def test_impressao_digital_estavel(self) -> None:
        contexto = ia.contexto_ia(self.montar())
        self.assertEqual(ia.impressao_digital(contexto), ia.impressao_digital(json.loads(json.dumps(contexto))))
        self.assertEqual(len(ia.impressao_digital(contexto)), 64)


class InterpretarTests(unittest.TestCase):
    def test_interpretar_leitura(self) -> None:
        puro = json.dumps(LEITURA, ensure_ascii=False)
        self.assertEqual(ia.interpretar_leitura(puro), LEITURA)
        self.assertEqual(ia.interpretar_leitura(f"```json\n{puro}\n```"), LEITURA)
        sem_chave = {k: v for k, v in LEITURA.items() if k != "olharAgora"}
        self.assertIsNone(ia.interpretar_leitura(json.dumps(sem_chave)))
        self.assertIsNone(ia.interpretar_leitura(json.dumps({**LEITURA, "funciona": "  "})))
        self.assertIsNone(ia.interpretar_leitura("texto livre"))


class LeituraTests(BaseCockpit):
    def setUp(self) -> None:
        super().setUp()
        patcher = patch(FABRICA)
        patcher.start()
        self.addCleanup(patcher.stop)

    def linhas(self) -> int:
        return self.db.execute(select(func.count()).select_from(MetaAdsCockpitLeitura)).scalar_one()

    def test_gerar_e_obter(self) -> None:
        provedor = provedor_ok()
        gerada = ia.gerar_leitura(self.db, self.emp_id, self.filtro(), provedor=provedor)
        self.assertEqual(gerada.leitura.manchete, LEITURA["manchete"])
        self.assertIsNone(gerada.aviso)
        mensagens, temperatura = provedor.chamadas[0]
        self.assertEqual((mensagens[0]["content"], temperatura), (ia.PROMPT_LEITURA, 0.3))
        self.assertEqual(
            json.loads(mensagens[1]["content"]), ia.contexto_ia(ck.montar(self.db, self.emp_id, self.filtro()))
        )
        obtida = ia.obter_leitura(self.db, self.emp_id, self.filtro())
        self.assertEqual(obtida.leitura, gerada.leitura)
        self.assertFalse(obtida.desatualizada)
        self.assertTrue(obtida.iaDisponivel)
        self.assertIsNotNone(obtida.geradoEm)

    def test_obter_sem_leitura(self) -> None:
        r = ia.obter_leitura(self.db, self.emp_id, self.filtro())
        self.assertIsNone(r.leitura)
        self.assertIsNone(r.texto)
        self.assertFalse(r.desatualizada)

    def test_ia_indisponivel(self) -> None:
        with patch(FABRICA, side_effect=RuntimeError("sem chave")):
            r = ia.obter_leitura(self.db, self.emp_id, self.filtro())
        self.assertFalse(r.iaDisponivel)

    def test_resposta_sem_json_vira_texto(self) -> None:
        r = ia.gerar_leitura(self.db, self.emp_id, self.filtro(), provedor=ProvedorFalso("Tudo bem por aqui."))
        self.assertIsNone(r.leitura)
        self.assertEqual(r.texto, "Tudo bem por aqui.")
        self.assertEqual(ia.obter_leitura(self.db, self.emp_id, self.filtro()).texto, "Tudo bem por aqui.")

    def test_gerar_de_novo_substitui(self) -> None:
        ia.gerar_leitura(self.db, self.emp_id, self.filtro(), provedor=ProvedorFalso("Primeira."))
        ia.gerar_leitura(self.db, self.emp_id, self.filtro(), provedor=provedor_ok())
        self.assertEqual(self.linhas(), 1)
        self.assertIsNotNone(ia.obter_leitura(self.db, self.emp_id, self.filtro()).leitura)

    def test_mudar_meta_desatualiza(self) -> None:
        ia.gerar_leitura(self.db, self.emp_id, self.filtro(), provedor=provedor_ok())
        atualizar_config(self.db, self.emp_id, MetaAdsMonitorConfigUpdate(metaCpl=200))
        r = ia.obter_leitura(self.db, self.emp_id, self.filtro())
        self.assertTrue(r.desatualizada)
        self.assertIsNotNone(r.leitura)

    def test_falha_mantem_guardada(self) -> None:
        ia.gerar_leitura(self.db, self.emp_id, self.filtro(), provedor=provedor_ok())
        antes = self.db.execute(select(MetaAdsCockpitLeitura)).scalar_one()
        digest, gerado = antes.mclDigest, antes.mclGeradoEm
        r = ia.gerar_leitura(
            self.db, self.emp_id, self.filtro(), provedor=ProvedorFalso(erro=RuntimeError("fora do ar"))
        )
        self.assertEqual(r.leitura.manchete, LEITURA["manchete"])
        self.assertTrue(r.aviso.startswith(PREFIXO_AVISO))
        self.assertIn("fora do ar", r.aviso)
        self.db.expire_all()
        depois = self.db.execute(select(MetaAdsCockpitLeitura)).scalar_one()
        self.assertEqual((depois.mclDigest, depois.mclGeradoEm, depois.mclLeitura["leitura"]), (digest, gerado, LEITURA))
        self.assertEqual(self.linhas(), 1)

    def test_falha_sem_guardada(self) -> None:
        r = ia.gerar_leitura(self.db, self.emp_id, self.filtro(), provedor=ProvedorFalso(erro=RuntimeError("x")))
        self.assertIsNone(r.leitura)
        self.assertTrue(r.aviso.startswith(PREFIXO_AVISO))
        self.assertEqual(self.linhas(), 0)

    def test_resposta_vazia_nao_grava(self) -> None:
        r = ia.gerar_leitura(self.db, self.emp_id, self.filtro(), provedor=ProvedorFalso("  "))
        self.assertTrue(r.aviso.startswith(PREFIXO_AVISO))
        self.assertEqual(self.linhas(), 0)

    def test_recorte_por_conta(self) -> None:
        ia.gerar_leitura(self.db, self.emp_id, self.filtro(mac_id=None), provedor=provedor_ok())
        ia.gerar_leitura(self.db, self.emp_id, self.filtro(mac_id=self.conta.macId), provedor=provedor_ok())
        ia.gerar_leitura(self.db, self.emp_id, self.filtro(somente_ativas=True), provedor=provedor_ok())
        self.assertEqual(self.linhas(), 3)
        macs = sorted(self.db.execute(select(MetaAdsCockpitLeitura.mclMacId)).scalars())
        self.assertEqual(macs, [0, 0, self.conta.macId])


class RotaTests(BaseCockpit):
    def setUp(self) -> None:
        super().setUp()
        app = FastAPI()
        app.include_router(meta_ads_router.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(usuId=1, usuAdmin=False)
        self.http = TestClient(app)
        self.h = {"X-Company-Id": str(self.emp_id)}
        self.url = "/api/meta-ads/cockpit/leitura?data_inicial=2026-10-01&data_final=2026-10-31"

    def test_gerar_e_obter_pela_rota(self) -> None:
        with patch.object(meta_ads_router, "require_user_in_company"), patch(FABRICA) as fabrica:
            fabrica.return_value = provedor_ok()
            vazia = self.http.get(self.url, headers=self.h)
            gerada = self.http.post(self.url, headers=self.h)
            obtida = self.http.get(self.url, headers=self.h)
            sem_datas = self.http.get("/api/meta-ads/cockpit/leitura", headers=self.h)
        self.assertEqual(vazia.status_code, 200, vazia.text)
        self.assertIsNone(vazia.json()["leitura"])
        self.assertEqual(gerada.status_code, 200, gerada.text)
        self.assertEqual(obtida.json()["leitura"]["manchete"], LEITURA["manchete"])
        self.assertFalse(obtida.json()["desatualizada"])
        self.assertEqual(sem_datas.status_code, 422)


if __name__ == "__main__":
    unittest.main()
