import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from backend.workers import meta_ads_worker as w


class ProximaExecucaoTests(unittest.TestCase):
    def test_antes_da_hora_no_mesmo_dia(self) -> None:
        # 05:00 UTC = 02:00 em Sao Paulo; proxima 04:00 SP = daqui 2h.
        agora = datetime(2026, 10, 14, 5, 0, tzinfo=timezone.utc)
        self.assertEqual(w.segundos_ate_proxima(agora, 4), 2 * 3600)

    def test_depois_da_hora_vai_para_amanha(self) -> None:
        # 12:00 UTC = 09:00 SP; proxima 04:00 SP = 19h depois.
        agora = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(w.segundos_ate_proxima(agora, 4), 19 * 3600)

    def test_exatamente_na_hora_vai_para_amanha(self) -> None:
        agora = datetime(2026, 10, 14, 7, 0, tzinfo=timezone.utc)  # 04:00 SP
        self.assertEqual(w.segundos_ate_proxima(agora, 4), 24 * 3600)


class ProximaHoraTests(unittest.TestCase):
    def test_segundos_ate_proxima_hora(self) -> None:
        self.assertEqual(
            w.segundos_ate_proxima_hora(datetime(2026, 10, 14, 10, 15, 30, tzinfo=timezone.utc)), 2670
        )
        self.assertEqual(
            w.segundos_ate_proxima_hora(datetime(2026, 10, 14, 10, 0, 0, tzinfo=timezone.utc)), 3600
        )


class CicloTests(unittest.TestCase):
    def test_ciclo_diario_avalia_alertas_depois_da_sync(self) -> None:
        ordem = []
        with patch(
            "backend.services.meta_ads.sincronizacao.sincronizar_todas_agendadas",
            side_effect=lambda: ordem.append("sync") or 1,
        ), patch(
            "backend.services.meta_ads.alertas.avaliar_diarios_todas",
            side_effect=lambda hoje: ordem.append(("alertas", hoje)) or 1,
        ):
            w._ciclo()
        self.assertEqual(ordem[0], "sync")
        self.assertEqual(ordem[1][0], "alertas")

    def test_ciclo_horario_so_avalia_alertas(self) -> None:
        with patch("backend.services.meta_ads.alertas.avaliar_horarios_todas", return_value=2) as avaliar:
            w._ciclo_horario()
        avaliar.assert_called_once()
        self.assertIsNotNone(avaliar.call_args.args[0].tzinfo)


if __name__ == "__main__":
    unittest.main()
