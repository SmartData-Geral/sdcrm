import unittest
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from backend.services.meta_ads import cockpit_regras as r

m = r.Metas(150, 10, 1.5, 150)


class RegrasCockpitTests(unittest.TestCase):
    def test_metas(self):
        self.assertEqual(m.custo_mql_implicito, 1500)

    def test_metas_da_config(self):
        cfg = SimpleNamespace(
            mmcMetaCpl=Decimal("150.00"), mmcMetaTaxaMql=Decimal("10.00"),
            mmcCplFator=Decimal("1.50"), mmcGastoSemLead=Decimal("150.00"),
        )
        self.assertEqual(r.metas_da_config(cfg), m)

    def test_taxa(self):
        self.assertEqual(r.taxa(2, 7), 28.57)
        self.assertIsNone(r.taxa(1, 0))

    def test_selo_cpl(self):
        self.assertEqual(r.selo_cpl(150, m), "bom")
        self.assertEqual(r.selo_cpl(225, m), "atencao")
        self.assertEqual(r.selo_cpl(225.01, m), "ruim")
        self.assertEqual(r.selo_cpl(None, m), "sem_dados")

    def test_selo_taxa_mql(self):
        self.assertEqual(r.selo_taxa_mql(1, 10, m), "bom")
        self.assertEqual(r.selo_taxa_mql(6, 100, m), "atencao")
        self.assertEqual(r.selo_taxa_mql(5, 100, m), "ruim")
        self.assertEqual(r.selo_taxa_mql(0, 0, m), "sem_dados")

    def test_selo_custo_mql(self):
        self.assertEqual(r.selo_custo_mql(1500, m), "bom")
        self.assertEqual(r.selo_custo_mql(2250, m), "atencao")
        self.assertEqual(r.selo_custo_mql(2675.33, m), "ruim")
        self.assertEqual(r.selo_custo_mql(None, m), "sem_dados")

    def test_saude_periodo(self):
        self.assertEqual(r.saude_periodo("atencao", "ruim"), "ruim")
        self.assertEqual(r.saude_periodo("sem_dados", "bom"), "sem_dados")
        self.assertEqual(r.saude_periodo("bom", "sem_dados"), "bom")
        self.assertEqual(r.saude_periodo("bom", "atencao"), "atencao")

    def test_gargalo(self):
        self.assertEqual(r.gargalo(36, 3, 1, 0), "mql")
        self.assertEqual(r.gargalo(10, 5, 1, 0), "oportunidade")
        self.assertIsNone(r.gargalo(2, 1, 1, 0))
        self.assertEqual(r.gargalo(10, 5, 5, 0), "contrato")
        self.assertEqual(r.gargalo(10, 5, 4, 2), "mql")

    def test_frase_gargalo(self):
        self.assertEqual(r.frase_gargalo("mql", 36, 3), "Para cada 12 leads no CRM, só 1 vira MQL.")
        self.assertEqual(r.frase_gargalo("mql", 36, 0), "Nenhum dos 36 leads no CRM virou MQL.")
        self.assertEqual(r.frase_gargalo("oportunidade", 9, 3), "Para cada 3 MQLs, só 1 vira oportunidade.")
        self.assertEqual(r.frase_gargalo("contrato", 4, 0), "Nenhuma das 4 oportunidades virou contrato.")
        self.assertIsNone(r.frase_gargalo("mql", 3, 3))

    def test_classificar_dados_reais(self):
        c = r.classificar_anuncio(2522.88, 8, 7, 2, m)
        self.assertEqual((c.quadrante, c.cpl, c.taxa_mql, c.amostra_pequena), ("otimizar_custo", 315.36, 28.57, False))
        c = r.classificar_anuncio(1778.29, 15, 14, 1, m)
        self.assertEqual((c.quadrante, c.cpl), ("rever_publico", 118.55))
        c = r.classificar_anuncio(1162.89, 3, 3, 0, m)
        self.assertEqual((c.quadrante, c.amostra_pequena), ("pausar", True))
        c = r.classificar_anuncio(90, 1, 1, 1, m)
        self.assertEqual((c.quadrante, c.amostra_pequena), ("escalar", True))

    def test_classificar_sem_lead(self):
        c = r.classificar_anuncio(100, 0, 0, 0, m)
        self.assertEqual((c.quadrante, c.motivo), ("aguardar_dados", "sem_lead"))
        self.assertEqual(r.classificar_anuncio(150, 0, 0, 0, m).quadrante, "pausar")
        c = r.classificar_anuncio(200, 2, 0, 0, m)
        self.assertEqual((c.quadrante, c.motivo), ("aguardar_dados", "sem_crm"))
        c = r.classificar_anuncio(100, 0, 2, 1, m)
        self.assertEqual((c.cpl, c.quadrante), (50, "escalar"))

    def test_amostra_pequena(self):
        c4 = r.classificar_anuncio(90, 4, 4, 1, m)
        self.assertTrue(c4.amostra_pequena)
        self.assertTrue(r.recomendacao(c4, True)[1].endswith("Amostra pequena: menos de 5 leads."))
        self.assertFalse(r.classificar_anuncio(90, 5, 5, 1, m).amostra_pequena)

    def test_recomendacao_pausado(self):
        c = r.classificar_anuncio(1162.89, 3, 3, 0, m)
        rotulo, porque = r.recomendacao(c, False)
        self.assertEqual(rotulo, "Manter pausado")
        self.assertIn("(já pausado)", porque)
        self.assertEqual(r.recomendacao(r.classificar_anuncio(90, 5, 5, 1, m), True)[0], "Escalar")
        self.assertEqual(
            r.recomendacao(r.classificar_anuncio(100, 0, 0, 0, m), True),
            ("Aguardar dados", "Gasto ainda baixo e nenhum lead: aguardar mais dados."),
        )

    def test_periodo_anterior(self):
        self.assertEqual(
            r.periodo_anterior(date(2026, 10, 1), date(2026, 10, 31)), (date(2026, 8, 31), date(2026, 9, 30))
        )
        self.assertEqual(
            r.periodo_anterior(date(2026, 1, 1), date(2026, 10, 27)), (date(2025, 3, 7), date(2025, 12, 31))
        )

    def test_intervalos(self):
        tipo, itens = r.intervalos(date(2026, 1, 1), date(2026, 10, 27))
        self.assertEqual((tipo, len(itens)), ("mes", 10))
        self.assertEqual(itens[-1], (date(2026, 10, 1), date(2026, 10, 27), "out/2026"))
        tipo, itens = r.intervalos(date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(tipo, "semana")
        self.assertEqual([(a.day, b.day) for a, b, _ in itens], [(1, 4), (5, 11), (12, 18), (19, 25), (26, 31)])
        self.assertEqual(itens[1][2], "05/10–11/10")
        ini = date(2026, 1, 1)
        self.assertEqual(r.intervalos(ini, ini + timedelta(days=61))[0], "semana")
        self.assertEqual(r.intervalos(ini, ini + timedelta(days=62))[0], "mes")


if __name__ == "__main__":
    unittest.main()
