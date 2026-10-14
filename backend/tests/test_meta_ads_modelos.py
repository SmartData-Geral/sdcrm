import unittest
from datetime import date

from sqlalchemy.exc import IntegrityError

from backend.tests import banco_sqlite as b


class ModelosMetaAdsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)

    def test_conta_duplicada_na_mesma_empresa_e_recusada(self) -> None:
        b.criar_conta(self.db, self.emp.empId, act="act_1")
        with self.assertRaises(IntegrityError):
            b.criar_conta(self.db, self.emp.empId, act="act_1")

    def test_mesma_conta_em_empresas_diferentes_e_permitida(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        b.criar_conta(self.db, self.emp.empId, act="act_1")
        b.criar_conta(self.db, outra.empId, act="act_1")

    def test_insight_duplicado_no_mesmo_dia_e_recusado(self) -> None:
        conta = b.criar_conta(self.db, self.emp.empId)
        camp = b.criar_campanha(self.db, conta, "c1", "Campanha 1")
        b.criar_insight(self.db, camp, date(2026, 10, 1), 10)
        with self.assertRaises(IntegrityError):
            b.criar_insight(self.db, camp, date(2026, 10, 1), 20)

    def test_apagar_campanha_desliga_a_oportunidade(self) -> None:
        conta = b.criar_conta(self.db, self.emp.empId)
        camp = b.criar_campanha(self.db, conta, "c1", "Campanha 1")
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoMcgId=camp.mcgId)
        self.db.delete(camp)
        self.db.commit()
        self.db.refresh(opo)
        self.assertIsNone(opo.opoMcgId)
        self.assertFalse(opo.opoMcgManual)


if __name__ == "__main__":
    unittest.main()
