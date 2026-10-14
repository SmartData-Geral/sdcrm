import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import get_current_user
from backend.database import get_db
from backend.routers import meta_ads_router
from backend.tests import banco_sqlite as b

TOKEN = "EAAB-token-de-teste-rotas-4321"


class RotasTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.usuario = SimpleNamespace(usuId=1, usuAdmin=True)
        app = FastAPI()
        app.include_router(meta_ads_router.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.usuario
        self.http = TestClient(app)
        self.h = {"X-Company-Id": str(self.emp.empId)}

    def _criar(self):
        r = self.http.post(
            "/api/meta-ads/contas",
            headers=self.h,
            json={"macNome": "Conta", "macContaExterna": "act_9", "token": TOKEN, "origens": []},
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def test_criar_e_listar_sem_token(self) -> None:
        self._criar()
        r = self.http.get("/api/meta-ads/contas", headers=self.h)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(TOKEN, r.text)
        self.assertEqual(r.json()["items"][0]["macTokenFinal"], "4321")

    def test_nao_admin_bloqueado(self) -> None:
        self.usuario.usuAdmin = False
        r = self.http.get("/api/meta-ads/contas", headers=self.h)
        self.assertEqual(r.status_code, 403)

    def test_sincronizar_duas_vezes_da_409(self) -> None:
        conta = self._criar()
        with patch.object(meta_ads_router.sincronizacao, "executar_em_sessao_propria") as rodar:
            r1 = self.http.post(f"/api/meta-ads/contas/{conta['macId']}/sincronizar", headers=self.h)
            r2 = self.http.post(f"/api/meta-ads/contas/{conta['macId']}/sincronizar", headers=self.h)
        self.assertEqual(r1.status_code, 202, r1.text)
        self.assertEqual(r2.status_code, 409)
        rodar.assert_called_once_with(conta["macId"], "manual")

    def test_periodo_invalido_da_422(self) -> None:
        r = self.http.post(
            "/api/meta-ads/sincronizar-periodo",
            headers=self.h,
            json={"data_inicial": "2026-10-10", "data_final": "2026-10-01"},
        )
        self.assertEqual(r.status_code, 422)

    def test_periodo_dispara_para_contas_ativas(self) -> None:
        conta = self._criar()
        with patch.object(meta_ads_router.sincronizacao, "executar_em_sessao_propria") as rodar:
            r = self.http.post(
                "/api/meta-ads/sincronizar-periodo",
                headers=self.h,
                json={"data_inicial": "2026-09-01", "data_final": "2026-09-30"},
            )
        self.assertEqual(r.status_code, 202, r.text)
        self.assertEqual(r.json()["contas"], [conta["macId"]])
        args = rodar.call_args.args
        self.assertEqual((args[0], args[1], str(args[2]), str(args[3])), (conta["macId"], "periodo", "2026-09-01", "2026-09-30"))


if __name__ == "__main__":
    unittest.main()
