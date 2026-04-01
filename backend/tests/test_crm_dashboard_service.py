import unittest

from backend.services.crm_dashboard_service import _calculate_forecast_value


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


if __name__ == "__main__":
    unittest.main()
