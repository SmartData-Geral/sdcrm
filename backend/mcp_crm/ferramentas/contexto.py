from sqlalchemy import select

from mcp.server.mcpserver import Context

from ...models.como_conheceu import ComoConheceu
from ...models.empresa import Empresa
from ...models.etapa_kanban import EtapaKanban
from ...models.motivo_cancelamento import MotivoCancelamento
from ...models.produto import Produto
from ...models.usuario import Usuario
from ...models.usuario_empresa import UsuarioEmpresa
from ..ferramenta import executar_ferramenta
from ..servidor import mcp
from ._comum import hoje


@mcp.tool()
def contexto(ctx: Context) -> dict:
    """Situa o agente: empresa da chave, nome e escopos da chave, responsável padrão
    (autor das anotações feitas pelo MCP), data de hoje e pipelines de venda.
    Chame esta ferramenta primeiro."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "contexto", escrita=False, argumentos=argumentos) as s:
        empresa = s.db.get(Empresa, s.empId)
        responsavel = s.db.get(Usuario, s.usuResponsavelPadraoId) if s.usuResponsavelPadraoId else None
        pipelines = s.db.scalars(
            select(EtapaKanban.etkPipeline)
            .where(EtapaKanban.etkEmpId == s.empId, EtapaKanban.etkAtivo.is_(True))
            .distinct()
            .order_by(EtapaKanban.etkPipeline)
        ).all()
        return {
            "empresa": {"id": s.empId, "nome": empresa.empNome if empresa else None},
            "chave": {"nome": s.nome, "escopos": sorted(s.escopos)},
            "responsavel_padrao": (
                {"id": responsavel.usuId, "nome": responsavel.usuNome} if responsavel else None
            ),
            "hoje": hoje().isoformat(),
            "pipelines": list(pipelines),
        }


@mcp.tool()
def listar_cadastros(ctx: Context) -> dict:
    """Lista, numa chamada, os cadastros ativos usados para filtrar e editar
    oportunidades: etapas por pipeline (na ordem do kanban), produtos, origens
    ("como conheceu"), motivos de perda e responsáveis. Use para descobrir IDs."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "listar_cadastros", escrita=False, argumentos=argumentos) as s:
        db, emp = s.db, s.empId
        etapas = db.scalars(
            select(EtapaKanban)
            .where(EtapaKanban.etkEmpId == emp, EtapaKanban.etkAtivo.is_(True))
            .order_by(EtapaKanban.etkPipeline, EtapaKanban.etkOrdem, EtapaKanban.etkId)
        ).all()
        produtos = db.scalars(
            select(Produto).where(Produto.proEmpId == emp, Produto.proAtivo.is_(True)).order_by(Produto.proNome)
        ).all()
        origens = db.scalars(
            select(ComoConheceu)
            .where(ComoConheceu.ccoEmpId == emp, ComoConheceu.ccoAtivo.is_(True))
            .order_by(ComoConheceu.ccoNome)
        ).all()
        motivos = db.scalars(
            select(MotivoCancelamento)
            .where(MotivoCancelamento.mcaEmpId == emp, MotivoCancelamento.mcaAtivo.is_(True))
            .order_by(MotivoCancelamento.mcaNome)
        ).all()
        responsaveis = db.execute(
            select(Usuario.usuId, Usuario.usuNome, Usuario.usuEmail)
            .join(UsuarioEmpresa, UsuarioEmpresa.useUsuId == Usuario.usuId)
            .where(UsuarioEmpresa.useEmpId == emp, Usuario.usuAtivo.is_(True))
            .order_by(Usuario.usuNome)
        ).all()

        por_pipeline: dict[str, list[dict]] = {}
        for e in etapas:
            por_pipeline.setdefault(e.etkPipeline, []).append({"id": e.etkId, "nome": e.etkNome, "ordem": e.etkOrdem})
        return {
            "etapas": por_pipeline,
            "produtos": [{"id": p.proId, "nome": p.proNome} for p in produtos],
            "origens": [{"id": o.ccoId, "nome": o.ccoNome, "grupo": o.ccoGrupo} for o in origens],
            "motivos_perda": [{"id": m.mcaId, "nome": m.mcaNome} for m in motivos],
            "responsaveis": [{"id": i, "nome": n, "email": e} for i, n, e in responsaveis],
        }
