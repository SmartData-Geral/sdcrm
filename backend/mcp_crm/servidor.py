"""Instância do servidor MCP do SDCRM e montagem do app ASGI."""

from __future__ import annotations

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from .autenticacao import AutenticacaoMCPASGI

INSTRUCOES = (
    "Servidor MCP do CRM SDCRM. Permite consultar e operar leads e oportunidades, o funil "
    "de vendas, o histórico de interações e os indicadores comerciais da empresa vinculada "
    "à chave do conector. Chame `contexto` primeiro e `listar_cadastros` para descobrir IDs "
    "de etapas, produtos, origens, motivos de perda e responsáveis. Antes de marcar ganho, "
    "perdido, stand-by ou reativar, confirme com o usuário, porque isso altera MRR e "
    "indicadores. Datas no formato YYYY-MM-DD."
)

mcp = MCPServer(
    name="SDCRM",
    title="SDCRM - CRM Smart Data",
    instructions=INSTRUCOES,
    version="1.0.0",
)


def build_mcp_asgi_app() -> AutenticacaoMCPASGI:
    """App Streamable HTTP (sem estado, JSON) atrás da autenticação por chave.

    Depois desta chamada, mcp.session_manager fica disponível para o lifespan."""
    from . import ferramentas  # noqa: F401  (registra as ferramentas)

    interno = mcp.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    return AutenticacaoMCPASGI(interno)
