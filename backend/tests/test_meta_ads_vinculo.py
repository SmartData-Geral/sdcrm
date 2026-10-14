import unittest
from unittest import mock

from backend.services import lead_intake_service
from backend.services.meta_ads import vinculo
from backend.tests import banco_sqlite as b

NOME = "CP030326 | LEADS | ABO | FRONTEND OFFER | PLAYBOOK | AD TESTING"


class NormalizacaoTests(unittest.TestCase):
    def test_minusculas_e_espacos(self) -> None:
        self.assertEqual(vinculo.normalizar_nome("  CP03  |  Leads \n"), "cp03 | leads")

    def test_vazio(self) -> None:
        self.assertEqual(vinculo.normalizar_nome(None), "")
        self.assertEqual(vinculo.normalizar_nome("   "), "")


class VinculoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.conta = b.criar_conta(self.db, self.emp.empId, act="act_1")
        self.camp = b.criar_campanha(self.db, self.conta, "120210000001", NOME)

    def test_liga_pelo_nome_em_utm_source(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME.lower() + "  ")
        self.assertTrue(vinculo.vincular_oportunidade(self.db, opo))
        self.assertEqual(opo.opoMcgId, self.camp.mcgId)

    def test_liga_pelo_id_da_campanha(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoUtmCampaign="120210000001")
        self.assertTrue(vinculo.vincular_oportunidade(self.db, opo))

    def test_sem_candidato_nao_liga(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId)
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))
        self.assertIsNone(opo.opoMcgId)

    def test_nome_ambiguo_nao_liga(self) -> None:
        outra = b.criar_conta(self.db, self.emp.empId, act="act_2")
        b.criar_campanha(self.db, outra, "999", NOME)
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME)
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))
        self.assertIsNone(opo.opoMcgId)

    def test_campanha_de_outra_empresa_nao_liga(self) -> None:
        outra_emp = b.criar_empresa(self.db, "Outra")
        opo = b.criar_oportunidade(self.db, outra_emp.empId, opoUtmSource=NOME)
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))

    def test_manual_e_preservado(self) -> None:
        opo = b.criar_oportunidade(
            self.db, self.emp.empId, opoUtmSource=NOME, opoMcgId=None, opoMcgManual=True
        )
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))
        self.assertIsNone(opo.opoMcgId)

    def test_ja_ligada_nao_muda(self) -> None:
        outra = b.criar_campanha(self.db, self.conta, "555", "Outra campanha")
        opo = b.criar_oportunidade(
            self.db, self.emp.empId, opoUtmSource=NOME, opoMcgId=outra.mcgId
        )
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))
        self.assertEqual(opo.opoMcgId, outra.mcgId)

    def test_vincular_pendentes_conta_e_respeita_regras(self) -> None:
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME)
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmTerm="120210000001")
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME, opoMcgManual=True)
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource="outra coisa")
        self.assertEqual(vinculo.vincular_pendentes(self.db, self.emp.empId), 2)


class HookEntradaDeLeadsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.conta = b.criar_conta(self.db, self.emp.empId, act="act_1")
        self.camp = b.criar_campanha(self.db, self.conta, "120210000001", NOME)

    def test_helper_liga_oportunidade_com_campanha(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME)
        lead_intake_service._vincular_campanha_meta(self.db, opo)
        self.assertEqual(opo.opoMcgId, self.camp.mcgId)

    def test_falha_no_vinculo_nao_propaga_e_sessao_segue_usavel(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME)
        opo_id = opo.opoId
        with mock.patch(
            "backend.services.lead_intake_service.vinculo_meta_ads.vincular_oportunidade",
            side_effect=RuntimeError("falha simulada"),
        ):
            with self.assertLogs("backend.services.lead_intake_service", level="ERROR"):
                lead_intake_service._vincular_campanha_meta(self.db, opo)
        self.db.commit()
        persistida = self.db.get(b.Oportunidade, opo_id)
        self.assertIsNotNone(persistida)
        self.assertIsNone(persistida.opoMcgId)

    def test_falha_no_vinculo_usa_savepoint(self) -> None:
        db = mock.MagicMock()
        opo = mock.MagicMock()
        with mock.patch(
            "backend.services.lead_intake_service.vinculo_meta_ads.vincular_oportunidade",
            side_effect=RuntimeError("falha simulada"),
        ):
            with self.assertLogs("backend.services.lead_intake_service", level="ERROR"):
                lead_intake_service._vincular_campanha_meta(db, opo)
        db.begin_nested.assert_called_once()
        db.begin_nested.return_value.__exit__.assert_called_once()


if __name__ == "__main__":
    unittest.main()
