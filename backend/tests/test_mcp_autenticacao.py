import asyncio
import json
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.mcp_crm.autenticacao import (
    AutenticacaoMCPASGI,
    FiltroChaveNoLogAcesso,
    autenticar_chave,
    caminho_efetivo,
    instalar_filtro_log_acesso,
)

MOD = "backend.mcp_crm.autenticacao"
CHAVE = "sdcrm_0123456789ab_" + "A" * 43


class AppInterno:
    def __init__(self) -> None:
        self.scope = None

    async def __call__(self, scope, receive, send):
        self.scope = scope


def _chamar(wrapper, scope):
    enviados = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(msg):
        enviados.append(msg)

    asyncio.run(wrapper(scope, receive, send))
    return enviados


def _scope(path, root_path="", headers=None):
    return {
        "type": "http",
        "method": "POST",
        "path": path,
        "raw_path": path.encode(),
        "root_path": root_path,
        "headers": headers or [],
        "client": ("10.0.0.1", 5000),
    }


class CaminhoEfetivoTests(unittest.TestCase):
    def test_mount_do_starlette_com_root_path(self) -> None:
        self.assertEqual(caminho_efetivo(_scope(f"/api/mcp/{CHAVE}/", "/api/mcp")), f"/{CHAVE}/")

    def test_sem_root_path(self) -> None:
        self.assertEqual(caminho_efetivo(_scope(f"/{CHAVE}")), f"/{CHAVE}")

    def test_root_path_que_nao_prefixa_o_path(self) -> None:
        self.assertEqual(caminho_efetivo(_scope(f"/api/mcp/{CHAVE}", "/crm/api/mcp")), f"/{CHAVE}")


class WrapperTests(unittest.TestCase):
    def test_chave_no_caminho_injeta_id_e_reescreve_path(self) -> None:
        interno = AppInterno()
        with patch(f"{MOD}.autenticar_chave", return_value=11) as auth:
            _chamar(AutenticacaoMCPASGI(interno), _scope(f"/api/mcp/{CHAVE}", "/api/mcp"))
        self.assertEqual(auth.call_args[0][0], CHAVE)
        self.assertEqual(interno.scope["path"], "/")
        self.assertEqual(interno.scope["root_path"], "")
        self.assertIn((b"x-sdcrm-ich-id", b"11"), interno.scope["headers"])

    def test_chave_no_header_x_api_key(self) -> None:
        interno = AppInterno()
        headers = [(b"x-api-key", CHAVE.encode())]
        with patch(f"{MOD}.autenticar_chave", return_value=11) as auth:
            _chamar(AutenticacaoMCPASGI(interno), _scope("/api/mcp/", "/api/mcp", headers))
        self.assertEqual(auth.call_args[0][0], CHAVE)
        self.assertEqual(interno.scope["path"], "/")
        self.assertNotIn(b"x-api-key", [k for k, _ in interno.scope["headers"]])

    def test_header_interno_forjado_e_descartado(self) -> None:
        interno = AppInterno()
        headers = [(b"x-sdcrm-ich-id", b"999"), (b"X-Sdcrm-Outro", b"x")]
        with patch(f"{MOD}.autenticar_chave", return_value=11):
            _chamar(AutenticacaoMCPASGI(interno), _scope(f"/api/mcp/{CHAVE}", "/api/mcp", headers))
        internos = [(k, v) for k, v in interno.scope["headers"] if k.lower().startswith(b"x-sdcrm-")]
        self.assertEqual(internos, [(b"x-sdcrm-ich-id", b"11")])

    def test_chave_recusada_responde_401_sem_chamar_o_app(self) -> None:
        interno = AppInterno()
        with patch(f"{MOD}.autenticar_chave", return_value=None):
            enviados = _chamar(AutenticacaoMCPASGI(interno), _scope(f"/api/mcp/{CHAVE}", "/api/mcp"))
        self.assertIsNone(interno.scope)
        self.assertEqual(enviados[0]["status"], 401)
        self.assertEqual(json.loads(enviados[1]["body"]), {"detail": "Chave de API invalida ou revogada"})

    def test_lifespan_passa_direto(self) -> None:
        interno = AppInterno()
        _chamar(AutenticacaoMCPASGI(interno), {"type": "lifespan"})
        self.assertEqual(interno.scope, {"type": "lifespan"})

    def test_websocket_e_fechado_sem_chamar_o_app(self) -> None:
        interno = AppInterno()
        scope = {
            "type": "websocket",
            "path": f"/api/mcp/{CHAVE}",
            "root_path": "/api/mcp",
            "headers": [],
        }
        enviados = _chamar(AutenticacaoMCPASGI(interno), scope)
        self.assertIsNone(interno.scope)
        self.assertEqual(enviados, [{"type": "websocket.close", "code": 1008}])


class AutenticarChaveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.p_sessao = patch(f"{MOD}.SessionLocal", return_value=self.db)
        self.p_log = patch(f"{MOD}.integracao_log_service.registrar")
        self.p_sessao.start()
        self.registrar = self.p_log.start()

    def tearDown(self) -> None:
        self.p_log.stop()
        self.p_sessao.stop()

    def test_chave_com_escopo_mcp_devolve_id(self) -> None:
        chave = SimpleNamespace(ichId=11, ichEscopos="mcp:read")
        with patch(f"{MOD}.integracao_chave_service.autenticar", return_value=chave):
            self.assertEqual(autenticar_chave(CHAVE, metodo="POST", ip=None, user_agent=None), 11)
        self.registrar.assert_not_called()
        self.db.close.assert_called_once()

    def test_chave_sem_escopo_mcp_e_recusada_e_logada_so_com_prefixo(self) -> None:
        chave = SimpleNamespace(ichId=11, ichEscopos="leads:write")
        with patch(f"{MOD}.integracao_chave_service.autenticar", return_value=chave):
            self.assertIsNone(autenticar_chave(CHAVE, metodo="POST", ip="1.2.3.4", user_agent="n8n"))
        log = self.registrar.call_args.kwargs
        self.assertEqual((log["status_http"], log["resultado"], log["rota"]), (401, "unauthorized", "mcp"))
        self.assertEqual(log["prefixo_informado"], "sdcrm_0123456789ab")
        self.assertNotIn(CHAVE, json.dumps(log, default=str))

    def test_chave_invalida_e_recusada(self) -> None:
        with patch(f"{MOD}.integracao_chave_service.autenticar", return_value=None):
            self.assertIsNone(autenticar_chave("lixo", metodo="POST", ip=None, user_agent=None))
        self.assertEqual(self.registrar.call_args.kwargs["prefixo_informado"], "(malformado)")


def _registro_acesso_uvicorn(path: str) -> logging.LogRecord:
    """Um LogRecord no mesmo formato que uvicorn.access usa (%-args, não f-string)."""
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:12345", "POST", path, "1.1", 200),
        exc_info=None,
    )


class FiltroLogAcessoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = logging.getLogger("uvicorn.access")
        self.logger_erro = logging.getLogger("uvicorn.error")
        self._filtros_originais = list(self.logger.filters)
        self._filtros_originais_erro = list(self.logger_erro.filters)

    def tearDown(self) -> None:
        self.logger.filters = self._filtros_originais
        self.logger_erro.filters = self._filtros_originais_erro

    def test_mascara_o_segredo_mantendo_o_prefixo(self) -> None:
        registro = _registro_acesso_uvicorn(f"/api/mcp/{CHAVE}")
        self.assertTrue(FiltroChaveNoLogAcesso().filter(registro))
        mensagem = registro.getMessage()
        self.assertNotIn(CHAVE, mensagem)
        self.assertIn("sdcrm_0123456789ab_***", mensagem)

    def test_registro_sem_chave_fica_inalterado(self) -> None:
        registro = _registro_acesso_uvicorn("/api/health")
        self.assertTrue(FiltroChaveNoLogAcesso().filter(registro))
        self.assertIn("/api/health", registro.getMessage())

    def test_instalar_duas_vezes_adiciona_um_filtro_so_em_cada_logger(self) -> None:
        """uvicorn loga o handshake de websocket recusado (fechado com 1008 pelo
        wrapper) em uvicorn.error, com o path completo -- inclusive a chave -- por
        isso o filtro precisa estar em uvicorn.access E uvicorn.error."""
        instalar_filtro_log_acesso()
        instalar_filtro_log_acesso()
        for logger in (self.logger, self.logger_erro):
            instalados = [f for f in logger.filters if isinstance(f, FiltroChaveNoLogAcesso)]
            self.assertEqual(len(instalados), 1)


if __name__ == "__main__":
    unittest.main()
