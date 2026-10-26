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


if __name__ == "__main__":
    unittest.main()
