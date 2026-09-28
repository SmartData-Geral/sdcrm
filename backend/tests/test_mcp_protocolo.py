import unittest
from unittest.mock import MagicMock, patch

from mcp.client import Client

import backend.mcp_crm.ferramentas  # noqa: F401  (registra as ferramentas)
from backend.mcp_crm import mcp
from backend.tests.mcp_apoio import contexto_falso, oportunidade_falsa

FERRAMENTAS = {
    "contexto", "listar_cadastros", "buscar_oportunidades", "obter_oportunidade",
    "listar_historico", "resumo_funil", "obter_indicadores", "detalhar_indicador",
    "obter_metas", "criar_lead", "atualizar_oportunidade", "mover_etapa",
    "atualizar_qualificacao", "registrar_interacao", "marcar_ganho", "marcar_perdido",
    "colocar_stand_by", "reativar_oportunidade",
}
ESCRITA = {
    "criar_lead", "atualizar_oportunidade", "mover_etapa", "atualizar_qualificacao",
    "registrar_interacao", "marcar_ganho", "marcar_perdido", "colocar_stand_by",
    "reativar_oportunidade",
}
FER = "backend.mcp_crm.ferramenta"


class ProtocoloTests(unittest.IsolatedAsyncioTestCase):
    def _autenticar(self, escopos=("mcp:read", "mcp:write")):
        sessao = contexto_falso(escopos=escopos)
        return [
            patch(f"{FER}.SessionLocal", return_value=MagicMock()),
            patch(f"{FER}.ich_id_do_contexto", return_value=11),
            patch(f"{FER}.carregar_contexto", return_value=sessao),
            patch(f"{FER}.integracao_log_service.registrar"),
        ]

    async def test_lista_as_18_ferramentas_com_esquemas(self) -> None:
        async with Client(mcp) as client:
            resultado = await client.list_tools()
        por_nome = {t.name: t for t in resultado.tools}
        self.assertEqual(set(por_nome), FERRAMENTAS)
        for nome, tool in por_nome.items():
            with self.subTest(nome=nome):
                self.assertTrue(tool.description)
                self.assertNotIn("ctx", tool.input_schema.get("properties", {}))
        score = por_nome["atualizar_qualificacao"].input_schema["properties"]["lead_score"]
        self.assertIn("10", str(score))

    async def test_erro_chega_como_is_error_com_mensagem(self) -> None:
        patches = self._autenticar()
        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(patches)])
        async with Client(mcp) as client:
            r = await client.call_tool("atualizar_qualificacao", {"oportunidade_id": 5})
        self.assertTrue(r.is_error)
        self.assertIn("Informe ao menos um campo de qualificação.", r.content[0].text)

    async def test_chave_so_leitura_nao_escreve(self) -> None:
        patches = self._autenticar(escopos=("mcp:read",))
        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(patches)])
        async with Client(mcp) as client:
            r = await client.call_tool("mover_etapa", {"oportunidade_id": 5, "etapa_id": 2})
        self.assertTrue(r.is_error)
        self.assertIn("mcp:write", r.content[0].text)

    async def test_sucesso_de_ponta_a_ponta(self) -> None:
        patches = self._autenticar() + [
            patch("backend.mcp_crm.ferramentas.fechamento.obter_oportunidade_ativa", return_value=oportunidade_falsa()),
            patch("backend.mcp_crm.ferramentas.fechamento.responder_oportunidade", return_value={"id": 5}),
        ]
        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(patches)])
        async with Client(mcp) as client:
            r = await client.call_tool("reativar_oportunidade", {"oportunidade_id": 5})
        self.assertFalse(r.is_error)
        # O texto é JSON e pode vir com acentos escapados; a chave "aviso" é ASCII.
        self.assertIn('"aviso"', r.content[0].text)


if __name__ == "__main__":
    unittest.main()
