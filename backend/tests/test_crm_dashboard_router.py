import unittest

from fastapi import HTTPException

from backend.routers.crm_dashboard_router import _parse_dashboard_oportunidades_params


class ParseDrillParamsTests(unittest.TestCase):
    def test_aceita_todas_as_metricas_suportadas_pelo_servico(self) -> None:
        for metrica in (
            "recebidas",
            "ganhas",
            "perdidas",
            "ativas",
            "mrrIncremental",
            "valorProjeto",
        ):
            with self.subTest(metrica=metrica):
                params = _parse_dashboard_oportunidades_params(metrica=metrica)
                self.assertEqual(params.metrica, metrica)

    def test_metrica_ausente_e_permitida(self) -> None:
        self.assertIsNone(_parse_dashboard_oportunidades_params().metrica)

    def test_metrica_desconhecida_retorna_422(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            _parse_dashboard_oportunidades_params(metrica="inexistente")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_status_invalido_cai_para_todas(self) -> None:
        self.assertEqual(_parse_dashboard_oportunidades_params(status="xpto").status, "todas")


if __name__ == "__main__":
    unittest.main()
