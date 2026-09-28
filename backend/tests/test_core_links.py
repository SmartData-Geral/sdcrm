import os
import unittest
from unittest.mock import patch

from backend.core.links import url_da_oportunidade


class UrlDaOportunidadeTests(unittest.TestCase):
    def test_monta_link_com_base_publica(self) -> None:
        with patch.dict(os.environ, {"VITE_PUBLIC_BASE_URL": "https://crm.exemplo.com/crm/"}):
            self.assertEqual(url_da_oportunidade(42), "https://crm.exemplo.com/crm/oportunidades/42")

    def test_sem_base_devolve_none(self) -> None:
        with patch.dict(os.environ, {"VITE_PUBLIC_BASE_URL": ""}):
            self.assertIsNone(url_da_oportunidade(42))

    def test_base_sem_esquema_devolve_none(self) -> None:
        with patch.dict(os.environ, {"VITE_PUBLIC_BASE_URL": "crm.exemplo.com"}):
            self.assertIsNone(url_da_oportunidade(42))


if __name__ == "__main__":
    unittest.main()
