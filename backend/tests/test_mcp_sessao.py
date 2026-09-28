import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.core.tempo import utcnow
from backend.mcp_crm.sessao import (
    ErroMCP,
    carregar_contexto,
    escopos_da_chave,
    ich_id_do_contexto,
)


def _chave(**kw):
    base = dict(
        ichId=11,
        ichEmpId=7,
        ichNome="Claude",
        ichEscopos="leads:write,mcp:read",
        ichUsuResponsavelPadraoId=3,
        ichAtivo=True,
        ichRevogadaEm=None,
        ichExpiraEm=None,
        ichUltimoUsoEm=utcnow(),
    )
    base.update(kw)
    return SimpleNamespace(**base)


class IchIdDoContextoTests(unittest.TestCase):
    def test_le_o_header_interno(self) -> None:
        ctx = SimpleNamespace(headers={"x-sdcrm-ich-id": "11"})
        self.assertEqual(ich_id_do_contexto(ctx), 11)

    def test_sem_headers_e_nao_autenticado(self) -> None:
        with self.assertRaises(ErroMCP) as cm:
            ich_id_do_contexto(SimpleNamespace(headers=None))
        self.assertEqual(cm.exception.status_http, 401)
        self.assertIn("Verifique a URL do conector", cm.exception.mensagem)

    def test_header_nao_numerico_e_nao_autenticado(self) -> None:
        with self.assertRaises(ErroMCP):
            ich_id_do_contexto(SimpleNamespace(headers={"x-sdcrm-ich-id": "abc"}))


class CarregarContextoTests(unittest.TestCase):
    def test_chave_valida_monta_contexto_da_empresa_da_chave(self) -> None:
        db = MagicMock()
        db.get.return_value = _chave()
        ctx = carregar_contexto(db, 11)
        self.assertEqual((ctx.ichId, ctx.empId, ctx.nome, ctx.usuResponsavelPadraoId), (11, 7, "Claude", 3))
        self.assertEqual(ctx.escopos, frozenset({"leads:write", "mcp:read"}))
        self.assertIs(ctx.db, db)

    def test_chave_revogada_depois_de_conectar_e_recusada(self) -> None:
        db = MagicMock()
        db.get.return_value = _chave(ichRevogadaEm=utcnow())
        with self.assertRaises(ErroMCP) as cm:
            carregar_contexto(db, 11)
        self.assertEqual(cm.exception.mensagem, "Chave de API invalida ou revogada")
        self.assertEqual(cm.exception.resultado, "unauthorized")

    def test_chave_inexistente_e_recusada(self) -> None:
        db = MagicMock()
        db.get.return_value = None
        with self.assertRaises(ErroMCP):
            carregar_contexto(db, 11)

    def test_chave_sem_escopo_mcp_e_recusada(self) -> None:
        db = MagicMock()
        db.get.return_value = _chave(ichEscopos="leads:write")
        with self.assertRaises(ErroMCP):
            carregar_contexto(db, 11)


class EscoposDaChaveTests(unittest.TestCase):
    def test_ignora_espacos_e_vazios(self) -> None:
        self.assertEqual(
            escopos_da_chave(SimpleNamespace(ichEscopos=" mcp:read , ,mcp:write")),
            frozenset({"mcp:read", "mcp:write"}),
        )


if __name__ == "__main__":
    unittest.main()
