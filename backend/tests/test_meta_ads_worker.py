import unittest
from datetime import datetime, timezone

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


if __name__ == "__main__":
    unittest.main()
