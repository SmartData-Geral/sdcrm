"""
Teste de integração ponta a ponta do servidor MCP sobre HTTP real.

Diferente de test_mcp_protocolo.py (que usa o `Client` do SDK em memória contra
`backend.mcp_crm.mcp`, sem passar pelo wrapper ASGI de autenticação), este teste sobe o
app FastAPI de verdade (`backend.main.app`, que já monta `AutenticacaoMCPASGI` em
`/api/mcp`) e manda requisições JSON-RPC via `httpx.AsyncClient` com
`httpx.ASGITransport`, exercitando a extração da chave (path e header), a rejeição de
header `x-sdcrm-*` forjado e a resposta 401. Só o necessário é mockado: a validação da
chave (`autenticar_chave`), a sessão de banco e `carregar_contexto` de `ferramenta.py`
(sem tocar `ich_id_do_contexto`, que é o código real de extração do header interno) e o
log de integração.

IMPORTANTE sobre `StreamableHTTPSessionManager.run()`: só pode ser entrado uma vez por
instância/processo (`RuntimeError` na segunda vez -- ver
`mcp/server/streamable_http_manager.py`). Por isso todos os cenários rodam dentro de um
único `async with mcp.session_manager.run():`, num único método de teste, um cenário por
`subTest`, em vez de um `test_*` por cenário.

O servidor está em modo stateless + JSON (`stateless_http=True, json_response=True`): não
é preciso um `initialize` prévio nem `MCP-Protocol-Version` -- cada POST é atendido numa
transport nova e isolada (confirmado experimentalmente contra o SDK instalado em
`.venv/Lib/site-packages/mcp`).
"""

import unittest
from unittest.mock import MagicMock, patch

import httpx

from backend.main import app
from backend.mcp_crm import mcp
from backend.tests.mcp_apoio import contexto_falso

FER = "backend.mcp_crm.ferramenta"
AUT = "backend.mcp_crm.autenticacao"

CHAVE_VALIDA = "sdcrm_0123456789ab_" + "A" * 43

CABECALHOS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def _corpo_tools_call(nome: str, argumentos: dict, id_: int = 1) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": id_,
        "method": "tools/call",
        "params": {"name": nome, "arguments": argumentos},
    }


def _autenticar_chave_falsa(valor, **_kw):
    """Só a CHAVE_VALIDA autentica, com ichId 11 -- qualquer outra é recusada."""
    return 11 if valor == CHAVE_VALIDA else None


class MCPIntegracaoHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_plumbing_real_via_http(self) -> None:
        sessao = contexto_falso()
        ich_ids_recebidos: list[int] = []

        def carregar_contexto_falso(db, ich_id):
            ich_ids_recebidos.append(ich_id)
            return sessao

        patches = [
            patch(f"{AUT}.autenticar_chave", side_effect=_autenticar_chave_falsa),
            patch(f"{FER}.SessionLocal", return_value=MagicMock()),
            patch(f"{FER}.carregar_contexto", side_effect=carregar_contexto_falso),
            patch(f"{FER}.integracao_log_service.registrar"),
        ]
        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(patches)])

        # `atualizar_qualificacao` só com `oportunidade_id`: passa pela autenticação HTTP,
        # por ich_id_do_contexto e por carregar_contexto (mockado) antes de falhar dentro
        # da ferramenta com "Informe ao menos um campo de qualificação." -- prova a
        # plumbing completa sem precisar de banco de verdade.
        corpo = _corpo_tools_call("atualizar_qualificacao", {"oportunidade_id": 5})

        async with mcp.session_manager.run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                with self.subTest("chave no caminho"):
                    ich_ids_recebidos.clear()
                    r = await client.post(f"/api/mcp/{CHAVE_VALIDA}/", json=corpo, headers=CABECALHOS)
                    self.assertEqual(r.status_code, 200)
                    dados = r.json()
                    self.assertTrue(dados["result"]["isError"])
                    self.assertIn(
                        "Informe ao menos um campo de qualificação.", dados["result"]["content"][0]["text"]
                    )
                    self.assertEqual(ich_ids_recebidos, [11])

                with self.subTest("header x-sdcrm-ich-id forjado e ignorado"):
                    ich_ids_recebidos.clear()
                    cabecalhos = dict(CABECALHOS, **{"x-sdcrm-ich-id": "999"})
                    r = await client.post(f"/api/mcp/{CHAVE_VALIDA}/", json=corpo, headers=cabecalhos)
                    self.assertEqual(r.status_code, 200)
                    # carregar_contexto recebeu o ich_id 11 da chave autenticada pelo
                    # wrapper, nunca o 999 forjado no header de entrada.
                    self.assertEqual(ich_ids_recebidos, [11])

                with self.subTest("chave no header X-API-Key"):
                    ich_ids_recebidos.clear()
                    cabecalhos = dict(CABECALHOS, **{"X-API-Key": CHAVE_VALIDA})
                    r = await client.post("/api/mcp/", json=corpo, headers=cabecalhos)
                    self.assertEqual(r.status_code, 200)
                    dados = r.json()
                    self.assertTrue(dados["result"]["isError"])
                    self.assertEqual(ich_ids_recebidos, [11])

                with self.subTest("chave invalida"):
                    ich_ids_recebidos.clear()
                    r = await client.post("/api/mcp/sdcrm_lixolixolix1_" + "B" * 43 + "/", json=corpo, headers=CABECALHOS)
                    self.assertEqual(r.status_code, 401)
                    self.assertEqual(r.json(), {"detail": "Chave de API invalida ou revogada"})
                    # 401 vem do wrapper de autenticação, antes de qualquer chamada à ferramenta.
                    self.assertEqual(ich_ids_recebidos, [])


if __name__ == "__main__":
    unittest.main()
