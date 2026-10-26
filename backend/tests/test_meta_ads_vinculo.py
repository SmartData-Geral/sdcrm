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

    def test_liga_pelo_id_da_campanha_da_meta(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoMetaCampanhaId="120210000001")
        self.assertTrue(vinculo.vincular_oportunidade(self.db, opo))
        self.assertEqual(opo.opoMcgId, self.camp.mcgId)

    def test_id_da_campanha_da_meta_vence_o_utm(self) -> None:
        b.criar_campanha(self.db, self.conta, "555", "Outra campanha")
        opo = b.criar_oportunidade(
            self.db, self.emp.empId, opoMetaCampanhaId="120210000001", opoUtmSource="outra campanha"
        )
        self.assertTrue(vinculo.vincular_oportunidade(self.db, opo))
        self.assertEqual(opo.opoMcgId, self.camp.mcgId)

    def test_id_da_campanha_da_meta_respeita_manual(self) -> None:
        opo = b.criar_oportunidade(
            self.db, self.emp.empId, opoMetaCampanhaId="120210000001", opoMcgManual=True
        )
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))
        self.assertIsNone(opo.opoMcgId)

    def test_id_da_campanha_de_outra_empresa_nao_liga(self) -> None:
        outra_emp = b.criar_empresa(self.db, "Outra")
        opo = b.criar_oportunidade(self.db, outra_emp.empId, opoMetaCampanhaId="120210000001")
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))
        self.assertIsNone(opo.opoMcgId)

    def test_vincular_pendentes_usa_id_da_campanha_da_meta(self) -> None:
        b.criar_campanha(self.db, self.conta, "555", "Outra campanha")
        ligada = b.criar_oportunidade(
            self.db, self.emp.empId, opoMetaCampanhaId="120210000001", opoUtmSource="outra campanha"
        )
        manual = b.criar_oportunidade(
            self.db, self.emp.empId, opoMetaCampanhaId="120210000001", opoMcgManual=True
        )
        ids = (ligada.opoId, manual.opoId)
        self.assertEqual(vinculo.vincular_pendentes(self.db, self.emp.empId), 1)
        self.db.expire_all()
        self.assertEqual(self.db.get(b.Oportunidade, ids[0]).opoMcgId, self.camp.mcgId)
        self.assertIsNone(self.db.get(b.Oportunidade, ids[1]).opoMcgId)

    def test_vincular_pendentes_conta_e_respeita_regras(self) -> None:
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME)
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmTerm="120210000001")
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME, opoMcgManual=True)
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource="outra coisa")
        self.assertEqual(vinculo.vincular_pendentes(self.db, self.emp.empId), 2)

    def test_ligar_se_pendente_nao_sobrescreve_manual(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME, opoMcgManual=True)
        opo_id = opo.opoId
        self.assertFalse(vinculo._ligar_se_pendente(self.db, opo_id, self.camp.mcgId))
        self.db.expire_all()
        self.assertIsNone(self.db.get(b.Oportunidade, opo_id).opoMcgId)

    def test_ligar_se_pendente_nao_sobrescreve_ja_ligada(self) -> None:
        outra = b.criar_campanha(self.db, self.conta, "555", "Outra campanha")
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoMcgId=outra.mcgId)
        opo_id = opo.opoId
        self.assertFalse(vinculo._ligar_se_pendente(self.db, opo_id, self.camp.mcgId))
        self.db.expire_all()
        self.assertEqual(self.db.get(b.Oportunidade, opo_id).opoMcgId, outra.mcgId)

    def test_ligar_se_pendente_liga_pendente(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME)
        opo_id = opo.opoId
        self.assertTrue(vinculo._ligar_se_pendente(self.db, opo_id, self.camp.mcgId))
        self.db.expire_all()
        self.assertEqual(self.db.get(b.Oportunidade, opo_id).opoMcgId, self.camp.mcgId)


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


class VinculoPorAnuncioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.conta = b.criar_conta(self.db, self.emp.empId, act="act_1")
        self.camp = b.criar_campanha(self.db, self.conta, "120210000001", NOME)
        self.conj = b.criar_conjunto(self.db, self.camp, "555", "Conj")
        self.anuncio = b.criar_anuncio(self.db, self.conj, "999", "Anuncio")

    def test_vincular_pendentes_resolve_por_anuncio(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoMetaAnuncioId="999")
        opo_id = opo.opoId
        self.assertEqual(vinculo.vincular_pendentes(self.db, self.emp.empId), 1)
        self.db.expire_all()
        salva = self.db.get(b.Oportunidade, opo_id)
        self.assertEqual(salva.opoManId, self.anuncio.manId)
        self.assertEqual(salva.opoMcgId, self.camp.mcgId)

    def test_manual_nao_e_sobrescrito_pelo_anuncio(self) -> None:
        opo = b.criar_oportunidade(
            self.db, self.emp.empId, opoMetaAnuncioId="999", opoMcgManual=True
        )
        opo_id = opo.opoId
        vinculo.vincular_pendentes(self.db, self.emp.empId)
        self.db.expire_all()
        salva = self.db.get(b.Oportunidade, opo_id)
        self.assertIsNone(salva.opoMcgId)
        self.assertEqual(salva.opoManId, self.anuncio.manId)

    def test_campanha_ja_ligada_nao_e_trocada_pelo_anuncio(self) -> None:
        outra = b.criar_campanha(self.db, self.conta, "555", "Outra campanha")
        opo = b.criar_oportunidade(
            self.db, self.emp.empId, opoMetaAnuncioId="999", opoMcgId=outra.mcgId
        )
        opo_id = opo.opoId
        vinculo.vincular_pendentes(self.db, self.emp.empId)
        self.db.expire_all()
        salva = self.db.get(b.Oportunidade, opo_id)
        self.assertEqual(salva.opoMcgId, outra.mcgId)
        self.assertEqual(salva.opoManId, self.anuncio.manId)

    def test_vincular_oportunidade_prefere_anuncio_ao_utm(self) -> None:
        outra = b.criar_campanha(self.db, self.conta, "777", "Outra campanha")
        opo = b.criar_oportunidade(
            self.db, self.emp.empId, opoMetaAnuncioId="999", opoUtmSource="outra campanha"
        )
        self.assertTrue(vinculo.vincular_oportunidade(self.db, opo))
        self.assertEqual(opo.opoMcgId, self.camp.mcgId)
        self.assertNotEqual(opo.opoMcgId, outra.mcgId)

    def test_vincular_oportunidade_manual_sem_campanha_nao_ganha_campanha_do_anuncio(self) -> None:
        opo = b.criar_oportunidade(
            self.db, self.emp.empId, opoMetaAnuncioId="999", opoMcgManual=True, opoMcgId=None
        )
        vinculo.vincular_oportunidade(self.db, opo)
        self.assertIsNone(opo.opoMcgId)
        self.assertEqual(opo.opoManId, self.anuncio.manId)

    def test_anuncio_de_outra_empresa_nao_liga(self) -> None:
        outra_emp = b.criar_empresa(self.db, "Outra")
        opo = b.criar_oportunidade(self.db, outra_emp.empId, opoMetaAnuncioId="999")
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))
        self.assertIsNone(opo.opoManId)


if __name__ == "__main__":
    unittest.main()
