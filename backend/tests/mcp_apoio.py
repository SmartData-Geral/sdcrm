"""Fábricas compartilhadas pelos testes do MCP."""

from contextlib import contextmanager
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.mcp_crm.sessao import ContextoMCP


def contexto_falso(escopos=("mcp:read", "mcp:write"), emp_id=7, usu_padrao=3, nome="Claude"):
    return ContextoMCP(
        db=MagicMock(),
        ichId=11,
        empId=emp_id,
        nome=nome,
        escopos=frozenset(escopos),
        usuResponsavelPadraoId=usu_padrao,
    )


def usar_sessao(modulo: str, sessao: ContextoMCP):
    """Troca executar_ferramenta do módulo de ferramentas por uma versão que só entrega `sessao`."""

    @contextmanager
    def _falso(ctx, nome, *, escrita, argumentos, opo_id=None):
        sessao.opo_id = opo_id
        yield sessao

    return patch(f"{modulo}.executar_ferramenta", _falso)


def oportunidade_falsa(**kw):
    base = dict(
        opoId=5,
        opoEmpId=7,
        opoTitulo="BI para Acme",
        opoNomeContato="Maria",
        opoEmpresaContato="Acme",
        opoEmail="maria@acme.com",
        opoTelefone="11999990000",
        opoSolucao="Dashboards",
        opoProId=1,
        opoEtkId=4,
        opoUsuResponsavelId=2,
        opoCcoId=3,
        opoMcaId=None,
        opoLeadScore=8,
        opoTemperatura="quente",
        opoReuniaoConfirmada=True,
        opoPropostaEnviada=False,
        opoDataRecebimento=date(2026, 9, 1),
        opoValorOportunidade=12000,
        opoReceitaPontual=False,
        opoDataUltimoContato=date(2026, 9, 20),
        opoDataFechamento=None,
        opoFechadoRecorrencia=None,
        opoValorFechado=None,
        opoStatusFechamento=None,
        opoDoresMotivadores="Planilhas",
        opoComentarios=None,
        opoOrigemSistema=None,
        opoUtmSource=None,
        opoUtmCampaign=None,
        opoOpoAnteriorId=None,
        opoAtivo=True,
        opoDataCriacao=datetime(2026, 9, 1, 10, 0),
        opoDataAtualizacao=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)
