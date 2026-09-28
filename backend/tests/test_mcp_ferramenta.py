import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

from backend.exceptions import AuthorizationError, BadRequestError, ConflictError, NotFoundError
from backend.mcp_crm import ferramenta
from backend.mcp_crm.ferramenta import executar_ferramenta, traduzir_excecao
from backend.mcp_crm.sessao import ErroMCP
from backend.schemas.lead_integracao import LeadIntakeRequest
from backend.tests.mcp_apoio import contexto_falso

MOD = "backend.mcp_crm.ferramenta"


class TraduzirExcecaoTests(unittest.TestCase):
    def test_tabela_de_traducao(self) -> None:
        casos = [
            (BadRequestError("Etapa inválida"), (400, "bad_request", "Etapa inválida")),
            (AuthorizationError("Sem acesso"), (403, "forbidden", "Sem acesso")),
            (NotFoundError("Oportunidade não encontrada"), (404, "not_found", "Oportunidade não encontrada")),
            (ConflictError("Lead em processamento"), (409, "conflict", "Lead em processamento")),
            (ErroMCP("Sem escrita", 403, "forbidden"), (403, "forbidden", "Sem escrita")),
            (ValueError("Data inválida"), (400, "bad_request", "Data inválida")),
            (RuntimeError("boom"), (500, "error", "Erro interno ao executar a ferramenta.")),
        ]
        for exc, esperado in casos:
            with self.subTest(exc=type(exc).__name__):
                self.assertEqual(traduzir_excecao(exc), esperado)

    def test_validacao_do_lead_vira_mensagem_limpa(self) -> None:
        try:
            LeadIntakeRequest(source="mcp", name="Maria")
        except ValidationError as exc:
            status, resultado, mensagem = traduzir_excecao(exc)
        self.assertEqual((status, resultado), (400, "bad_request"))
        self.assertTrue(mensagem.startswith("Informe um e-mail válido ou um telefone com DDD."))
        self.assertNotIn("Value error", mensagem)


class ExecutarFerramentaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.sessao = contexto_falso(escopos=("mcp:read",))
        self.sessao.db = self.db
        self.patches = [
            patch(f"{MOD}.SessionLocal", return_value=self.db),
            patch(f"{MOD}.ich_id_do_contexto", return_value=11),
            patch(f"{MOD}.carregar_contexto", return_value=self.sessao),
            patch(f"{MOD}.integracao_log_service.registrar"),
        ]
        for p in self.patches:
            p.start()
        self.registrar = ferramenta.integracao_log_service.registrar

    def tearDown(self) -> None:
        for p in reversed(self.patches):
            p.stop()

    def _log(self) -> dict:
        self.assertEqual(self.registrar.call_count, 1)
        return self.registrar.call_args.kwargs

    def test_sucesso_registra_ok_com_opo_id(self) -> None:
        with executar_ferramenta(None, "obter_oportunidade", escrita=False, argumentos={"ctx": object(), "oportunidade_id": 5}, opo_id=5) as s:
            self.assertIs(s, self.sessao)
        log = self._log()
        self.assertEqual(log["rota"], "mcp:obter_oportunidade")
        self.assertEqual(log["metodo"], "TOOL")
        self.assertEqual((log["status_http"], log["resultado"]), (200, "ok"))
        self.assertEqual((log["emp_id"], log["ich_id"], log["opo_id"]), (7, 11, 5))
        self.assertEqual(log["payload"], {"oportunidade_id": 5})
        self.db.close.assert_called_once()

    def test_argumentos_com_data_viram_json(self) -> None:
        with executar_ferramenta(None, "x", escrita=False, argumentos={"data": date(2026, 9, 27)}):
            pass
        self.assertEqual(self._log()["payload"], {"data": "2026-09-27"})

    def test_opo_id_definido_dentro_da_ferramenta_vai_para_o_log(self) -> None:
        with executar_ferramenta(None, "criar_lead", escrita=False, argumentos={}) as s:
            s.opo_id = 99
        self.assertEqual(self._log()["opo_id"], 99)

    def test_escrita_com_chave_so_leitura_e_recusada(self) -> None:
        with self.assertRaises(ToolError) as cm:
            with executar_ferramenta(None, "mover_etapa", escrita=True, argumentos={}):
                self.fail("não deveria executar")
        self.assertIn("mcp:write", str(cm.exception))
        log = self._log()
        self.assertEqual((log["status_http"], log["resultado"]), (403, "forbidden"))

    def test_erro_do_service_faz_rollback_e_traduz(self) -> None:
        with self.assertRaises(ToolError) as cm:
            with executar_ferramenta(None, "obter_oportunidade", escrita=False, argumentos={}, opo_id=5):
                raise NotFoundError("Oportunidade não encontrada")
        self.assertEqual(str(cm.exception), "Oportunidade não encontrada")
        self.db.rollback.assert_called()
        log = self._log()
        self.assertEqual((log["status_http"], log["resultado"]), (404, "not_found"))
        self.assertEqual(log["erro"], {"detalhe": "Oportunidade não encontrada"})
        self.db.close.assert_called_once()

    def test_erro_inesperado_nao_vaza_detalhe(self) -> None:
        with self.assertRaises(ToolError) as cm:
            with executar_ferramenta(None, "x", escrita=False, argumentos={}):
                raise RuntimeError("senha do banco")
        self.assertEqual(str(cm.exception), "Erro interno ao executar a ferramenta.")
        self.assertEqual(self._log()["status_http"], 500)

    def test_chave_recusada_registra_sem_empresa(self) -> None:
        with patch(f"{MOD}.carregar_contexto", side_effect=ErroMCP("Chave de API invalida ou revogada", 401, "unauthorized")):
            with self.assertRaises(ToolError):
                with executar_ferramenta(None, "x", escrita=False, argumentos={}):
                    self.fail("não deveria executar")
        log = self._log()
        self.assertEqual((log["status_http"], log["resultado"], log["emp_id"]), (401, "unauthorized", None))


if __name__ == "__main__":
    unittest.main()
