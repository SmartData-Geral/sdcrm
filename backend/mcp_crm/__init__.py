"""Servidor MCP do SDCRM (ver docs/superpowers/specs/2026-09-27-mcp-crm-design.md)."""

from .servidor import build_mcp_asgi_app, mcp

__all__ = ["build_mcp_asgi_app", "mcp"]
