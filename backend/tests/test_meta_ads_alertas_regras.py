import unittest
from datetime import datetime, timedelta

from backend.services.meta_ads import alertas as a

AGORA = datetime(2026, 10, 26, 12, 0)
DESDE = AGORA - timedelta(days=10)


class CplTests(unittest.TestCase):
    def test_dispara_acima_de_1_5x(self) -> None:
        d = a.regra_cpl(7, "Anúncio A", 184, 2, 280, 7, 1.5)
        self.assertEqual((d.tipo, d.chave), ("cpl", "anuncio:7"))
        self.assertEqual(
            d.mensagem,
            "CPL de ontem R$ 92,00 (2,3× a média de R$ 40,00 dos 7 dias anteriores).",
        )
        self.assertEqual(d.dados["man_id"], 7)

    def test_exatamente_1_5x_nao_dispara(self) -> None:
        self.assertIsNone(a.regra_cpl(7, "A", 60, 1, 80, 2, 1.5))

    def test_exige_leads_ontem_e_base(self) -> None:
        self.assertIsNone(a.regra_cpl(7, "A", 500, 0, 80, 2, 1.5))
        self.assertIsNone(a.regra_cpl(7, "A", 500, 1, 80, 0, 1.5))


class GastoTests(unittest.TestCase):
    def test_dispara(self) -> None:
        d = a.regra_gasto(3, "A", 150, 0, 150)
        self.assertEqual((d.tipo, d.chave), ("gasto", "anuncio:3"))
        self.assertIn("R$ 150,00", d.mensagem)

    def test_abaixo_do_limite_nao_dispara(self) -> None:
        self.assertIsNone(a.regra_gasto(3, "A", 149.99, 0, 150))

    def test_com_lead_nao_dispara(self) -> None:
        self.assertIsNone(a.regra_gasto(3, "A", 400, 1, 150))


class FrequenciaTests(unittest.TestCase):
    def test_dispara(self) -> None:
        d = a.regra_frequencia(3, "A", 3.4, 3)
        self.assertEqual((d.tipo, d.chave), ("frequencia", "anuncio:3"))
        self.assertIn("3,4", d.mensagem)

    def test_limite_exato_nao_dispara(self) -> None:
        self.assertIsNone(a.regra_frequencia(3, "A", 3.0, 3))


class CtrTests(unittest.TestCase):
    def test_dispara_com_queda_de_30_pct(self) -> None:
        d = a.regra_ctr(5, "A", 2.0, 5000, 1.39, 4000, 20, 30)
        self.assertEqual((d.tipo, d.chave), ("ctr", "anuncio:5"))
        self.assertIn("1,39", d.mensagem)

    def test_queda_exata_dispara_e_menor_nao(self) -> None:
        self.assertIsNotNone(a.regra_ctr(5, "A", 2.0, 5000, 1.4, 4000, 20, 30))
        self.assertIsNone(a.regra_ctr(5, "A", 2.0, 5000, 1.41, 4000, 20, 30))

    def test_guardas_de_volume_e_tempo(self) -> None:
        self.assertIsNone(a.regra_ctr(5, "A", 2.0, 5000, 0.5, 4000, 13, 30))
        self.assertIsNone(a.regra_ctr(5, "A", 2.0, 999, 0.5, 4000, 20, 30))
        self.assertIsNone(a.regra_ctr(5, "A", 2.0, 5000, 0.5, 999, 20, 30))
        self.assertIsNotNone(a.regra_ctr(5, "A", 2.0, 1000, 0.5, 1000, 14, 30))


class ParadoTests(unittest.TestCase):
    def test_anuncio_reprovado(self) -> None:
        for st in ("DISAPPROVED", "WITH_ISSUES"):
            d = a.regra_anuncio_reprovado(9, "A", st, "texto proibido")
            self.assertEqual((d.tipo, d.chave), ("parado", "anuncio:9"))
            self.assertIn("texto proibido", d.mensagem)
        self.assertIsNone(a.regra_anuncio_reprovado(9, "A", "ACTIVE", None))
        self.assertIsNone(a.regra_anuncio_reprovado(9, "A", None, None))
        self.assertIsNotNone(a.regra_anuncio_reprovado(9, "A", "DISAPPROVED", None))

    def test_conta(self) -> None:
        self.assertIsNone(a.regra_conta(1, "C", 1, None))
        self.assertIsNone(a.regra_conta(1, "C", None, None))
        esperado = {
            2: "desativada", 3: "pagamento pendente", 7: "em análise de risco",
            8: "pagamento pendente", 9: "período de carência",
            100: "encerrada", 101: "encerrada", 42: "status 42 na Meta",
        }
        for status, texto in esperado.items():
            d = a.regra_conta(1, "C", status, None)
            self.assertEqual((d.tipo, d.chave), ("parado", "conta:1"))
            self.assertIn(texto, d.mensagem)

    def test_campanha_sem_veicular(self) -> None:
        d = a.regra_campanha_sem_veicular(4, "Camp", "ACTIVE", 0)
        self.assertEqual((d.tipo, d.chave), ("parado", "campanha:4"))
        self.assertIsNone(a.regra_campanha_sem_veicular(4, "Camp", "ACTIVE", 1))
        self.assertIsNone(a.regra_campanha_sem_veicular(4, "Camp", "PAUSED", 0))


class SemContatoTests(unittest.TestCase):
    def test_dispara_apos_24h(self) -> None:
        rec = AGORA - timedelta(hours=25)
        d = a.regra_sem_contato(11, "Opp", "Maria", "11999990000", rec, AGORA, 24, DESDE)
        self.assertEqual((d.tipo, d.chave), ("sem_contato", "lead:11"))
        self.assertIn("Maria", d.mensagem)
        self.assertIn("11999990000", d.mensagem)
        self.assertEqual(d.dados["contato"], "Maria")
        self.assertEqual(d.dados["telefone"], "11999990000")

    def test_exatas_24h_nao_dispara(self) -> None:
        rec = AGORA - timedelta(hours=24)
        self.assertIsNone(a.regra_sem_contato(11, "Opp", "M", "1", rec, AGORA, 24, DESDE))

    def test_lead_anterior_a_desde_nao_dispara(self) -> None:
        rec = DESDE - timedelta(seconds=1)
        self.assertIsNone(a.regra_sem_contato(11, "Opp", "M", "1", rec, AGORA, 24, DESDE))

    def test_sem_telefone(self) -> None:
        rec = AGORA - timedelta(hours=30)
        d = a.regra_sem_contato(11, "Opp", "M", None, rec, AGORA, 24, DESDE)
        self.assertNotIn("None", d.mensagem)

    def test_unico_com_dados_pessoais(self) -> None:
        disparos = [
            a.regra_cpl(1, "A", 184, 2, 280, 7, 1.5),
            a.regra_gasto(1, "A", 200, 0, 150),
            a.regra_frequencia(1, "A", 4, 3),
            a.regra_ctr(1, "A", 2.0, 5000, 1.0, 4000, 20, 30),
            a.regra_anuncio_reprovado(1, "A", "DISAPPROVED", "x"),
            a.regra_conta(1, "C", 2, None),
            a.regra_campanha_sem_veicular(1, "K", "ACTIVE", 0),
        ]
        for d in disparos:
            self.assertIsNotNone(d)
            self.assertFalse({"contato", "telefone"} & set(d.dados), d.tipo)
            for v in d.dados.values():
                self.assertIsInstance(v, (int, float, type(None)))


if __name__ == "__main__":
    unittest.main()
