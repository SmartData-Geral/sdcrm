import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from backend.mcp_crm.ferramentas import historico, oportunidades
from backend.mcp_crm.serializacao import Nomes
from backend.tests.mcp_apoio import contexto_falso, oportunidade_falsa, usar_sessao

OPO = "backend.mcp_crm.ferramentas.oportunidades"
HIS = "backend.mcp_crm.ferramentas.historico"


def _pagina_historico(itens, total=None):
    return SimpleNamespace(items=itens, total=total if total is not None else len(itens), page=1, page_size=10)


def _h(i):
    return SimpleNamespace(ophId=i, ophUsuId=None, ophDataRegistro=datetime(2026, 9, i, tzinfo=timezone.utc), ophConteudo=f"n{i}")


class BuscarOportunidadesTests(unittest.TestCase):
    def test_repassa_filtros_com_empresa_da_chave_e_limita_pagina(self) -> None:
        s = contexto_falso(emp_id=7)
        pagina = SimpleNamespace(items=[oportunidade_falsa()], total=1, page=1, page_size=50)
        with usar_sessao(OPO, s), \
             patch(f"{OPO}.oportunidade_service.list_oportunidades", return_value=pagina) as listar, \
             patch(f"{OPO}.carregar_nomes", return_value=Nomes()):
            r = oportunidades.buscar_oportunidades(
                ctx=None, texto="acme", status="ativo", temperatura="quente",
                ultimo_contato_ate=date(2026, 9, 1), por_pagina=500,
            )
        kwargs = listar.call_args.kwargs
        self.assertEqual(kwargs["company_id"], 7)
        self.assertEqual(kwargs["busca"], "acme")
        self.assertEqual(kwargs["status"], "ativos")
        self.assertEqual(kwargs["status_fechamento"], "ativo")
        self.assertEqual(kwargs["temperatura"], "quente")
        self.assertEqual(kwargs["data_ultimo_contato_fim"], date(2026, 9, 1))
        self.assertEqual((kwargs["page"], kwargs["page_size"]), (1, 50))
        self.assertEqual((r["total"], r["pagina"], r["por_pagina"]), (1, 1, 50))
        self.assertEqual(r["itens"][0]["id"], 5)


class ObterOportunidadeTests(unittest.TestCase):
    def test_traz_historico_recente_e_ciclo_anterior(self) -> None:
        s = contexto_falso(emp_id=7)
        opo = oportunidade_falsa(opoOpoAnteriorId=2)
        anterior = oportunidade_falsa(opoId=2, opoEmpId=7, opoTitulo="Ciclo 1", opoStatusFechamento="perdido")
        s.db.get.return_value = anterior
        with usar_sessao(OPO, s), \
             patch(f"{OPO}.obter_oportunidade_ativa", return_value=opo) as ativa, \
             patch(f"{OPO}.oportunidade_historico_service.list_historicos", return_value=_pagina_historico([_h(3)])) as lh, \
             patch(f"{OPO}.carregar_nomes", return_value=Nomes()), \
             patch(f"{OPO}.carregar_autores", return_value={}):
            r = oportunidades.obter_oportunidade(ctx=None, oportunidade_id=5)
        ativa.assert_called_once_with(s, 5)
        self.assertEqual(lh.call_args.kwargs, {"company_id": 7, "page": 1, "page_size": 10})
        self.assertEqual(r["historico_recente"][0]["conteudo"], "n3")
        self.assertEqual(r["ciclo_anterior"], {"id": 2, "titulo": "Ciclo 1", "status": "perdido"})

    def test_ciclo_anterior_de_outra_empresa_nao_aparece(self) -> None:
        s = contexto_falso(emp_id=7)
        s.db.get.return_value = oportunidade_falsa(opoId=2, opoEmpId=8)
        with usar_sessao(OPO, s), \
             patch(f"{OPO}.obter_oportunidade_ativa", return_value=oportunidade_falsa(opoOpoAnteriorId=2)), \
             patch(f"{OPO}.oportunidade_historico_service.list_historicos", return_value=_pagina_historico([])), \
             patch(f"{OPO}.carregar_nomes", return_value=Nomes()), \
             patch(f"{OPO}.carregar_autores", return_value={}):
            r = oportunidades.obter_oportunidade(ctx=None, oportunidade_id=5)
        self.assertIsNone(r["ciclo_anterior"])


class ListarHistoricoTests(unittest.TestCase):
    def test_confere_a_oportunidade_e_pagina(self) -> None:
        s = contexto_falso(emp_id=7)
        with usar_sessao(HIS, s), \
             patch(f"{HIS}.obter_oportunidade_ativa") as ativa, \
             patch(f"{HIS}.oportunidade_historico_service.list_historicos", return_value=_pagina_historico([_h(1), _h(2)], total=12)) as lh, \
             patch(f"{HIS}.carregar_autores", return_value={}):
            r = historico.listar_historico(ctx=None, oportunidade_id=5, pagina=2, por_pagina=2)
        ativa.assert_called_once_with(s, 5)
        self.assertEqual(lh.call_args.kwargs, {"company_id": 7, "page": 2, "page_size": 2})
        self.assertEqual((r["total"], r["pagina"], r["por_pagina"], len(r["itens"])), (12, 2, 2, 2))


if __name__ == "__main__":
    unittest.main()
