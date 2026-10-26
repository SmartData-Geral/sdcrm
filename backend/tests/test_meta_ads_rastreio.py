import unittest

from sqlalchemy import select

from backend.models.oportunidade_historico import OportunidadeHistorico
from backend.schemas.lead_integracao import LeadIntakeRequest
from backend.services import lead_intake_service
from backend.services.lead_normalizacao import normalizar_email, variantes_telefone
from backend.services.meta_ads import rastreio
from backend.tests import banco_sqlite as b


class LimparIdTests(unittest.TestCase):
    def test_limpar_id_meta(self) -> None:
        self.assertEqual(rastreio.limpar_id_meta("ag:120250133121060008"), "120250133121060008")
        self.assertEqual(rastreio.limpar_id_meta("l:1645"), "1645")
        self.assertEqual(rastreio.limpar_id_meta("p:+5575988666626"), "+5575988666626")
        self.assertEqual(rastreio.limpar_id_meta("as:77"), "77")
        self.assertEqual(rastreio.limpar_id_meta("c:88"), "88")
        self.assertIsNone(rastreio.limpar_id_meta("  "))
        self.assertIsNone(rastreio.limpar_id_meta(None))
        self.assertEqual(rastreio.limpar_id_meta("120"), "120")


class AplicarIdsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)

    def _historico(self, opo):
        return list(
            self.db.scalars(
                select(OportunidadeHistorico).where(OportunidadeHistorico.ophOpoId == opo.opoId)
            )
        )

    def test_aplica_ids_no_lead_novo(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId)
        ok = rastreio.aplicar_ids_meta(
            self.db, opo, meta_lead_id="l:1", campaign_id="c:2", adset_id="as:3", ad_id="ag:4"
        )
        self.assertTrue(ok)
        self.assertEqual(
            (opo.opoMetaLeadId, opo.opoMetaCampanhaId, opo.opoMetaConjuntoId, opo.opoMetaAnuncioId),
            ("1", "2", "3", "4"),
        )

    def test_reenvio_por_outro_anuncio_mantem_primeiro(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoMetaAnuncioId="A")
        ok = rastreio.aplicar_ids_meta(
            self.db, opo, meta_lead_id=None, campaign_id=None, adset_id=None, ad_id="ag:B"
        )
        self.db.flush()
        self.assertFalse(ok)
        self.assertEqual(opo.opoMetaAnuncioId, "A")
        notas = self._historico(opo)
        self.assertEqual(len(notas), 1)
        self.assertIn("B", notas[0].ophConteudo)

    def test_mesmo_anuncio_nao_gera_nota(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoMetaAnuncioId="A")
        ok = rastreio.aplicar_ids_meta(
            self.db, opo, meta_lead_id=None, campaign_id=None, adset_id=None, ad_id="A"
        )
        self.db.flush()
        self.assertTrue(ok)
        self.assertEqual(self._historico(opo), [])

    def test_nao_sobrescreve_ids_ja_preenchidos(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoMetaLeadId="9")
        rastreio.aplicar_ids_meta(
            self.db, opo, meta_lead_id="l:10", campaign_id="5", adset_id=None, ad_id=None
        )
        self.assertEqual(opo.opoMetaLeadId, "9")
        self.assertEqual(opo.opoMetaCampanhaId, "5")


class ApiDeLeadsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        conta = b.criar_conta(self.db, self.emp.empId, act="act_1")
        self.camp = b.criar_campanha(self.db, conta, "120210000001", "Camp")
        conj = b.criar_conjunto(self.db, self.camp, "555", "Conj")
        self.anuncio = b.criar_anuncio(self.db, conj, "999", "Anuncio")

    def _enviar(self, **extra):
        payload = LeadIntakeRequest(source="meta", email="a@b.com", name="Ana", **extra)
        return lead_intake_service._processar_com_lock(
            self.db,
            emp_id=self.emp.empId,
            ich_id=None,
            payload=payload,
            email_norm=normalizar_email(payload.email),
            fone_norm=None,
            fones=variantes_telefone(None),
        )

    def test_api_de_leads_grava_ids_e_resolve_anuncio(self) -> None:
        res = self._enviar(
            meta_lead_id="l:1645", campaign_id="c:120210000001", adset_id="as:555", ad_id="ag:999"
        )
        self.assertEqual(res.status, "created")
        opo = self.db.get(b.Oportunidade, res.opo_id)
        self.assertEqual(opo.opoMetaLeadId, "1645")
        self.assertEqual(opo.opoMetaAnuncioId, "999")
        self.assertEqual(opo.opoManId, self.anuncio.manId)
        self.assertEqual(opo.opoMcgId, self.anuncio.manMcgId)

    def test_reenvio_atualiza_sem_trocar_primeiro_anuncio(self) -> None:
        self._enviar(ad_id="ag:999")
        res = self._enviar(ad_id="ag:888")
        self.assertEqual(res.status, "updated")
        opo = self.db.get(b.Oportunidade, res.opo_id)
        self.assertEqual(opo.opoMetaAnuncioId, "999")
        notas = [h.ophConteudo for h in self.db.scalars(select(OportunidadeHistorico))]
        self.assertTrue(any("888" in n and "primeiro anúncio" in n for n in notas))




class CargaRetroativaTests(unittest.TestCase):
    def setUp(self) -> None:
        from datetime import datetime

        self.dt = datetime
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)

    def _item(self, meta_lead_id="999", dia=1, **extra):
        from backend.schemas.lead_integracao import RastreioMetaItem

        return RastreioMetaItem(
            meta_lead_id=meta_lead_id, created_time=self.dt(2026, 10, dia), **extra
        )

    def _rodar(self, itens, emp_id=None):
        resp = rastreio.aplicar_rastreio_retroativo(self.db, emp_id or self.emp.empId, itens)
        return resp

    def test_casa_por_lead_id_depois_telefone_depois_email(self) -> None:
        a = b.criar_oportunidade(self.db, self.emp.empId, opoMetaLeadId="111")
        c = b.criar_oportunidade(self.db, self.emp.empId, opoTelefoneNormalizado="5541999990000")
        d = b.criar_oportunidade(self.db, self.emp.empId, opoEmailNormalizado="x@y.com")
        resp = self._rodar(
            [
                self._item("l:111", 1, ad_id="ag:A1", campaign_id="c:C1", adset_id="as:S1"),
                self._item("222", 2, ad_id="ag:A2", phone="(41) 99999-0000"),
                self._item("333", 3, ad_id="ag:A3", email="X@Y.com"),
            ]
        )
        self.assertEqual((resp.casados, resp.nao_casados, resp.ambiguos, resp.ja_atribuidos), (3, 0, 0, 0))
        self.db.refresh(a), self.db.refresh(c), self.db.refresh(d)
        self.assertEqual((a.opoMetaAnuncioId, a.opoMetaCampanhaId, a.opoMetaConjuntoId), ("A1", "C1", "S1"))
        self.assertEqual((c.opoMetaAnuncioId, c.opoMetaLeadId), ("A2", "222"))
        self.assertEqual((d.opoMetaAnuncioId, d.opoMetaLeadId), ("A3", "333"))

    def test_sem_casamento_conta_nao_casado_e_nao_cria(self) -> None:
        from backend.models.oportunidade import Oportunidade

        b.criar_oportunidade(self.db, self.emp.empId)
        antes = len(list(self.db.scalars(select(Oportunidade))))
        resp = self._rodar([self._item("555", 1, ad_id="9", phone="41 98888-7777", email="n@n.com")])
        self.assertEqual((resp.casados, resp.nao_casados), (0, 1))
        self.assertEqual(len(list(self.db.scalars(select(Oportunidade)))), antes)

    def test_telefone_de_dois_leads_e_ambiguo(self) -> None:
        x = b.criar_oportunidade(self.db, self.emp.empId, opoTelefoneNormalizado="5541999990000")
        y = b.criar_oportunidade(self.db, self.emp.empId, opoTelefoneNormalizado="5541999990000")
        resp = self._rodar([self._item("1", 1, ad_id="A", phone="41999990000")])
        self.assertEqual((resp.ambiguos, resp.casados), (1, 0))
        self.db.refresh(x), self.db.refresh(y)
        self.assertIsNone(x.opoMetaAnuncioId)
        self.assertIsNone(y.opoMetaAnuncioId)

    def test_linhas_repetidas_primeira_vence_e_idempotente(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoTelefoneNormalizado="5541999990000")
        itens = [
            self._item("20", 5, ad_id="B", phone="41999990000"),
            self._item("10", 1, ad_id="A", phone="41999990000"),
        ]
        r1 = self._rodar(itens)
        self.assertEqual((r1.casados, r1.ja_atribuidos), (1, 1))
        self.db.refresh(opo)
        self.assertEqual(opo.opoMetaAnuncioId, "A")
        r2 = self._rodar(itens)
        self.assertEqual((r2.casados, r2.ja_atribuidos), (0, 2))
        self.db.refresh(opo)
        self.assertEqual((opo.opoMetaAnuncioId, opo.opoMetaLeadId), ("A", "10"))

    def test_outra_empresa_nao_e_tocada(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        alheia = b.criar_oportunidade(self.db, outra.empId, opoMetaLeadId="111")
        resp = self._rodar([self._item("111", 1, ad_id="A")])
        self.assertEqual((resp.casados, resp.nao_casados), (0, 1))
        self.db.refresh(alheia)
        self.assertIsNone(alheia.opoMetaAnuncioId)

    def test_inativa_nao_casa(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoMetaLeadId="111", opoAtivo=False)
        resp = self._rodar([self._item("111", 1, ad_id="A")])
        self.assertEqual(resp.nao_casados, 1)
        self.db.refresh(opo)
        self.assertIsNone(opo.opoMetaAnuncioId)


class RotaRastreioTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from backend.api_key import ApiKeyContext, get_api_key_context
        from backend.database import get_db
        from backend.routers import lead_intake_router

        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.escopos = frozenset({"leads:write"})
        app = FastAPI()
        app.include_router(lead_intake_router.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_api_key_context] = lambda: ApiKeyContext(
            ichId=None, empId=self.emp.empId, nome="n8n", escopos=self.escopos,
            usuResponsavelPadraoId=None,
        )
        self.http = TestClient(app)

    def _corpo(self, n=1):
        return {
            "itens": [
                {"meta_lead_id": str(i), "created_time": "2026-10-01T10:00:00", "ad_id": "ag:7",
                 "phone": "41999990000"}
                for i in range(n)
            ]
        }

    def test_rota_casa_e_responde(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoTelefoneNormalizado="5541999990000")
        r = self.http.post("/api/v1/leads/rastreio-meta", json=self._corpo())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"casados": 1, "nao_casados": 0, "ambiguos": 0, "ja_atribuidos": 0})
        self.db.refresh(opo)
        self.assertEqual(opo.opoMetaAnuncioId, "7")

    def test_mais_de_500_da_422(self) -> None:
        r = self.http.post("/api/v1/leads/rastreio-meta", json=self._corpo(501))
        self.assertEqual(r.status_code, 422)

    def test_sem_escopo_da_403(self) -> None:
        self.escopos = frozenset()
        r = self.http.post("/api/v1/leads/rastreio-meta", json=self._corpo())
        self.assertEqual(r.status_code, 403)

    def test_erro_500_nao_loga_dado_pessoal(self) -> None:
        from unittest.mock import patch

        from backend.models.integracao_requisicao_log import IntegracaoRequisicaoLog

        http = self.http.__class__(self.http.app, raise_server_exceptions=False)
        with patch.object(
            rastreio, "aplicar_rastreio_retroativo", side_effect=RuntimeError("tel +5541999990000")
        ):
            r = http.post("/api/v1/leads/rastreio-meta", json=self._corpo())
        self.assertEqual(r.status_code, 500)
        linhas = list(self.db.scalars(select(IntegracaoRequisicaoLog)))
        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0].irlResultado, "error")
        self.assertNotIn("5541999990000", str(linhas[0].irlErroJson))
        self.assertIn("RuntimeError", str(linhas[0].irlErroJson))


if __name__ == "__main__":
    unittest.main()
