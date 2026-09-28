import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.mcp_crm.ferramentas import funil, indicadores
from backend.tests.mcp_apoio import contexto_falso, usar_sessao

FUN = "backend.mcp_crm.ferramentas.funil"
IND = "backend.mcp_crm.ferramentas.indicadores"


def _resposta(dados: dict):
    r = MagicMock()
    r.model_dump.return_value = dados
    return r


class ResumoFunilTests(unittest.TestCase):
    def test_etapas_na_ordem_com_vazias_zeradas(self) -> None:
        s = contexto_falso()
        s.db.scalar.return_value = "default"
        s.db.scalars.return_value.all.return_value = [
            SimpleNamespace(etkId=1, etkNome="Novo"),
            SimpleNamespace(etkId=2, etkNome="Proposta"),
        ]
        s.db.execute.return_value.all.return_value = [(1, 3, Decimal("1500.00"))]
        with usar_sessao(FUN, s):
            r = funil.resumo_funil(ctx=None)
        self.assertEqual(
            r,
            {
                "pipeline": "default",
                "etapas": [
                    {"etapa": {"id": 1, "nome": "Novo"}, "quantidade": 3, "valor_total": 1500.0},
                    {"etapa": {"id": 2, "nome": "Proposta"}, "quantidade": 0, "valor_total": 0.0},
                ],
                "total_quantidade": 3,
                "total_valor": 1500.0,
            },
        )

    def test_empresa_sem_etapas(self) -> None:
        s = contexto_falso()
        s.db.scalar.return_value = None
        with usar_sessao(FUN, s):
            r = funil.resumo_funil(ctx=None)
        self.assertEqual(r, {"pipeline": None, "etapas": [], "total_quantidade": 0, "total_valor": 0.0})
        s.db.execute.assert_not_called()


class IndicadoresTests(unittest.TestCase):
    DASH = {
        "cards": {"recebidas": 10},
        "graficos": {"x": 1},
        "filtros": {"y": 1},
        "temMeta": True,
        "resumoMetas": {"z": 1},
        "motivosPerda": [],
        "serieMensal": [{"mes": "2026-01"}],
        "rankings": {},
    }

    def test_resumo_sem_graficos_e_sem_serie(self) -> None:
        s = contexto_falso(emp_id=7)
        with usar_sessao(IND, s), patch(f"{IND}.crm_dashboard_service.get_dashboard", return_value=_resposta(self.DASH)) as gd:
            r = indicadores.obter_indicadores(ctx=None, data_inicial=date(2026, 1, 1), status="ganhas")
        db, emp, filtros = gd.call_args[0]
        self.assertEqual(emp, 7)
        self.assertEqual((filtros.data_inicial, filtros.status, filtros.serie_anos), (date(2026, 1, 1), "ganhas", None))
        self.assertEqual(set(r), {"cards", "temMeta", "resumoMetas", "motivosPerda", "rankings"})

    def test_serie_mensal_quando_pedida(self) -> None:
        s = contexto_falso()
        with usar_sessao(IND, s), patch(f"{IND}.crm_dashboard_service.get_dashboard", return_value=_resposta(self.DASH)) as gd:
            r = indicadores.obter_indicadores(ctx=None, incluir_serie_mensal=True, anos_serie=[2025, 2026])
        self.assertEqual(gd.call_args[0][2].serie_anos, [2025, 2026])
        self.assertEqual(r["serieMensal"], [{"mes": "2026-01"}])

    def test_detalhar_indicador_avisa_truncamento(self) -> None:
        s = contexto_falso(emp_id=7)
        resp = _resposta({"itens": [{"id": 1}], "total": 150, "resumo": {}})
        with usar_sessao(IND, s), patch(f"{IND}.crm_dashboard_service.list_dashboard_oportunidades", return_value=resp) as lo:
            r = indicadores.detalhar_indicador(ctx=None, metrica="ganhas", periodo="2026-09")
        filtros = lo.call_args[0][2]
        self.assertEqual((filtros.metrica, filtros.periodo), ("ganhas", "2026-09"))
        self.assertTrue(r["truncado"])

    def test_detalhar_indicador_sem_truncamento(self) -> None:
        s = contexto_falso()
        resp = _resposta({"itens": [{"id": 1}], "total": 1, "resumo": {}})
        with usar_sessao(IND, s), patch(f"{IND}.crm_dashboard_service.list_dashboard_oportunidades", return_value=resp):
            self.assertFalse(indicadores.detalhar_indicador(ctx=None)["truncado"])

    def test_obter_metas(self) -> None:
        s = contexto_falso(emp_id=7)
        resp = _resposta({"items": [], "ano": 2026})
        with usar_sessao(IND, s), patch(f"{IND}.crm_meta_mensal_service.list_resumo_ano", return_value=resp) as lr:
            r = indicadores.obter_metas(ctx=None, ano=2026)
        lr.assert_called_once_with(s.db, company_id=7, ano=2026)
        self.assertEqual(r, {"items": [], "ano": 2026})


if __name__ == "__main__":
    unittest.main()
