import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from backend.mcp_crm.ferramentas import contexto as mod
from backend.models.empresa import Empresa
from backend.tests.mcp_apoio import contexto_falso, usar_sessao

MOD = "backend.mcp_crm.ferramentas.contexto"


class ContextoTests(unittest.TestCase):
    def test_contexto(self) -> None:
        s = contexto_falso(escopos=("mcp:write", "mcp:read"))
        s.db.get.side_effect = lambda modelo, _id: (
            SimpleNamespace(empId=7, empNome="Smart Data") if modelo is Empresa else SimpleNamespace(usuId=3, usuNome="Carlos")
        )
        s.db.scalars.return_value.all.return_value = ["default", "parcerias"]
        with usar_sessao(MOD, s), patch(f"{MOD}.hoje", return_value=date(2026, 9, 27)):
            r = mod.contexto(ctx=None)
        self.assertEqual(
            r,
            {
                "empresa": {"id": 7, "nome": "Smart Data"},
                "chave": {"nome": "Claude", "escopos": ["mcp:read", "mcp:write"]},
                "responsavel_padrao": {"id": 3, "nome": "Carlos"},
                "hoje": "2026-09-27",
                "pipelines": ["default", "parcerias"],
            },
        )

    def test_listar_cadastros(self) -> None:
        s = contexto_falso()
        s.db.scalars.return_value.all.side_effect = [
            [
                SimpleNamespace(etkId=1, etkNome="Novo", etkOrdem=1, etkPipeline="default"),
                SimpleNamespace(etkId=2, etkNome="Proposta", etkOrdem=2, etkPipeline="default"),
                SimpleNamespace(etkId=9, etkNome="Triagem", etkOrdem=1, etkPipeline="parcerias"),
            ],
            [SimpleNamespace(proId=1, proNome="BI")],
            [SimpleNamespace(ccoId=3, ccoNome="Site", ccoGrupo="Inbound")],
            [SimpleNamespace(mcaId=5, mcaNome="Preço")],
        ]
        s.db.execute.return_value.all.return_value = [(3, "Carlos", "carlos@x.com")]
        with usar_sessao(MOD, s):
            r = mod.listar_cadastros(ctx=None)
        self.assertEqual(
            r["etapas"],
            {
                "default": [{"id": 1, "nome": "Novo", "ordem": 1}, {"id": 2, "nome": "Proposta", "ordem": 2}],
                "parcerias": [{"id": 9, "nome": "Triagem", "ordem": 1}],
            },
        )
        self.assertEqual(r["produtos"], [{"id": 1, "nome": "BI"}])
        self.assertEqual(r["origens"], [{"id": 3, "nome": "Site", "grupo": "Inbound"}])
        self.assertEqual(r["motivos_perda"], [{"id": 5, "nome": "Preço"}])
        self.assertEqual(r["responsaveis"], [{"id": 3, "nome": "Carlos", "email": "carlos@x.com"}])


if __name__ == "__main__":
    unittest.main()
