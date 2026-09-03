import unittest

from backend.services.crm_dashboard_service import (
    _calculate_forecast_value,
    normalizar_metrica_drill,
    _resumo_meta_linha,
)


class CrmDashboardServiceTests(unittest.TestCase):
    def test_calculate_forecast_value_aplica_temperatura_e_lead_score(self) -> None:
        result = _calculate_forecast_value(1000, "quente", 8)
        self.assertEqual(result, 600.0)

    def test_calculate_forecast_value_retorna_zero_sem_dados_suficientes(self) -> None:
        self.assertEqual(_calculate_forecast_value(None, "quente", 10), 0.0)
        self.assertEqual(_calculate_forecast_value(1000, None, 10), 0.0)
        self.assertEqual(_calculate_forecast_value(1000, "morno", None), 0.0)

    def test_calculate_forecast_value_limita_lead_score_ao_intervalo_valido(self) -> None:
        self.assertEqual(_calculate_forecast_value(1000, "frio", 12), 250.0)
        self.assertEqual(_calculate_forecast_value(1000, "frio", -2), 0.0)


class NormalizarMetricaDrillTests(unittest.TestCase):
    def test_reconhece_valor_projeto_ignorando_caixa_e_espacos(self) -> None:
        self.assertEqual(normalizar_metrica_drill("valorProjeto"), "valor_projeto")
        self.assertEqual(normalizar_metrica_drill("  VALORPROJETO "), "valor_projeto")

    def test_reconhece_mrr_incremental(self) -> None:
        self.assertEqual(normalizar_metrica_drill("mrrIncremental"), "mrr_incremental")

    def test_mantem_metricas_simples(self) -> None:
        for metrica in ("recebidas", "ganhas", "perdidas", "ativas"):
            self.assertEqual(normalizar_metrica_drill(metrica), metrica)

    def test_retorna_none_para_desconhecida_ou_vazia(self) -> None:
        self.assertIsNone(normalizar_metrica_drill(None))
        self.assertIsNone(normalizar_metrica_drill(""))
        self.assertIsNone(normalizar_metrica_drill("qualquer"))


class ResumoMetaLinhaTests(unittest.TestCase):
    def test_meta_zero_e_tratada_como_ausente(self) -> None:
        linha = _resumo_meta_linha(0, 5000)
        self.assertIsNone(linha.meta)
        self.assertIsNone(linha.percentual)
        self.assertIsNone(linha.gap)
        self.assertEqual(linha.realizado, 5000.0)

    def test_calcula_percentual_e_gap_da_meta_de_projeto(self) -> None:
        linha = _resumo_meta_linha(20000, 15000)
        self.assertEqual(linha.meta, 20000.0)
        self.assertEqual(linha.percentual, 75.0)
        self.assertEqual(linha.gap, -5000.0)


if __name__ == "__main__":
    unittest.main()
