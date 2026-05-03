import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from backend.exceptions import ConflictError
from backend.schemas.crm_meta_mensal import CrmMetaMensalCreate
from backend.services.crm_meta_mensal_service import computar_derivados, create_meta


class CrmMetaMensalComputoTests(unittest.TestCase):
    def test_truncagem_fechamentos_exemplo_planejamento(self) -> None:
        qfe, mir = computar_derivados(
            6,
            Decimal("0.35"),
            Decimal("3500.00"),
        )
        self.assertEqual(qfe, 2)
        self.assertEqual(mir, Decimal("7000.00"))

    def test_mrr_incremental_produto_truncado(self) -> None:
        qfe, mir = computar_derivados(
            10,
            Decimal("0.25"),
            Decimal("2700.00"),
        )
        self.assertEqual(qfe, 2)
        self.assertEqual(mir, Decimal("5400.00"))


class CrmMetaMensalUnicidadeTests(unittest.TestCase):
    @patch("backend.services.crm_meta_mensal_service._existe_meta_mes", return_value=True)
    def test_create_meta_conflict_quando_mes_ja_existe(self, _: MagicMock) -> None:
        db = MagicMock()
        payload = CrmMetaMensalCreate(
            cmmMesReferencia=date(2026, 3, 1),
            cmmQtdRecebimento=12,
            cmmTaxaConversao=Decimal("0.30"),
            cmmMrrMedio=Decimal("3000.00"),
        )
        with self.assertRaises(ConflictError):
            create_meta(db, company_id=1, data=payload)


if __name__ == "__main__":
    unittest.main()
