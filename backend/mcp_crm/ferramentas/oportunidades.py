from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from mcp.server.mcpserver import Context

from ...core.links import url_da_oportunidade
from ...exceptions import BadRequestError
from ...models.oportunidade import Oportunidade
from ...schemas.lead_integracao import LeadIntakeRequest
from ...schemas.oportunidade import OportunidadeUpdate
from ...services import lead_intake_service, oportunidade_historico_service, oportunidade_service
from ..ferramenta import executar_ferramenta
from ..serializacao import carregar_autores, carregar_nomes, historico_item, oportunidade_completa, resumo_oportunidade, status_de
from ..servidor import mcp
from ._comum import (
    limitar_pagina,
    obter_oportunidade_ativa,
    responder_oportunidade,
    validar_origem,
    validar_produto,
    validar_responsavel,
)

Status = Literal["ativo", "ganho", "perdido", "stand-by"]
Temperatura = Literal["quente", "morno", "frio"]


@mcp.tool()
def buscar_oportunidades(
    ctx: Context,
    texto: str | None = None,
    status: Status | None = None,
    etapa_id: int | None = None,
    pipeline: str | None = None,
    responsavel_id: int | None = None,
    produto_id: int | None = None,
    temperatura: Temperatura | None = None,
    ultimo_contato_de: date | None = None,
    ultimo_contato_ate: date | None = None,
    pagina: Annotated[int, Field(ge=1)] = 1,
    por_pagina: Annotated[int, Field(ge=1)] = 20,
) -> dict:
    """Busca oportunidades/leads ativos no CRM, das mais novas para as mais antigas.
    `texto` procura em título, nome do contato, empresa e e-mail. Para achar leads
    parados, use `status="ativo"` com `ultimo_contato_ate`. Máximo de 50 por página."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "buscar_oportunidades", escrita=False, argumentos=argumentos) as s:
        pagina, por_pagina = limitar_pagina(pagina, por_pagina)
        resultado = oportunidade_service.list_oportunidades(
            s.db,
            company_id=s.empId,
            busca=texto,
            pipeline=pipeline,
            status="ativos",
            etapa_id=etapa_id,
            responsavel_id=responsavel_id,
            pro_id=produto_id,
            data_ultimo_contato_inicio=ultimo_contato_de,
            data_ultimo_contato_fim=ultimo_contato_ate,
            status_fechamento=status,
            temperatura=temperatura,
            page=pagina,
            page_size=por_pagina,
        )
        nomes = carregar_nomes(s.db, resultado.items)
        return {
            "itens": [resumo_oportunidade(o, nomes) for o in resultado.items],
            "total": resultado.total,
            "pagina": pagina,
            "por_pagina": por_pagina,
        }


@mcp.tool()
def obter_oportunidade(ctx: Context, oportunidade_id: int) -> dict:
    """Detalhe completo de uma oportunidade: dados do contato, etapa, responsável,
    qualificação, valores, fechamento, os 10 registros mais recentes do histórico,
    o ciclo anterior do mesmo contato (se houver) e o link para abrir no CRM."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "obter_oportunidade", escrita=False, argumentos=argumentos, opo_id=oportunidade_id) as s:
        opo = obter_oportunidade_ativa(s, oportunidade_id)
        dados = oportunidade_completa(opo, carregar_nomes(s.db, [opo]))
        historicos = oportunidade_historico_service.list_historicos(
            s.db, oportunidade_id, company_id=s.empId, page=1, page_size=10
        ).items
        autores = carregar_autores(s.db, historicos)
        dados["historico_recente"] = [historico_item(h, autores) for h in historicos]
        dados["ciclo_anterior"] = None
        if opo.opoOpoAnteriorId:
            anterior = s.db.get(Oportunidade, opo.opoOpoAnteriorId)
            if anterior is not None and anterior.opoEmpId == s.empId:
                dados["ciclo_anterior"] = {
                    "id": anterior.opoId,
                    "titulo": anterior.opoTitulo,
                    "status": status_de(anterior),
                }
        return dados


@mcp.tool()
def criar_lead(
    ctx: Context,
    nome: str | None = None,
    empresa: str | None = None,
    email: str | None = None,
    telefone: str | None = None,
    origem: Annotated[str, Field(min_length=2, max_length=60)] = "mcp",
    observacoes: str | None = None,
    responsavel_email: str | None = None,
    valor: Annotated[float | None, Field(ge=0)] = None,
) -> dict:
    """Cria um lead no CRM com a mesma regra da API de entrada: exige e-mail ou
    telefone, e se já existir oportunidade aberta do mesmo contato, atualiza em vez de
    duplicar (o retorno diz `status` created/updated e por qual critério deduplicou)."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "criar_lead", escrita=True, argumentos=argumentos) as s:
        payload = LeadIntakeRequest(
            source=origem,
            name=nome,
            company=empresa,
            email=email,
            phone=telefone,
            notes=observacoes,
            owner_email=responsavel_email,
            value=valor,
        )
        resultado = lead_intake_service.processar_lead(s.db, emp_id=s.empId, ich_id=s.ichId, payload=payload)
        s.opo_id = resultado.opo_id
        return {
            "status": resultado.status,
            "oportunidade_id": resultado.opo_id,
            "deduplicado_por": resultado.deduped_by,
            "ciclo_anterior_id": resultado.ciclo_anterior_id,
            "url": url_da_oportunidade(resultado.opo_id),
        }


@mcp.tool()
def atualizar_oportunidade(
    ctx: Context,
    oportunidade_id: int,
    titulo: Annotated[str | None, Field(max_length=300)] = None,
    contato: Annotated[str | None, Field(max_length=200)] = None,
    empresa: Annotated[str | None, Field(max_length=200)] = None,
    email: str | None = None,
    telefone: Annotated[str | None, Field(max_length=50)] = None,
    solucao: Annotated[str | None, Field(max_length=500)] = None,
    produto_id: int | None = None,
    responsavel_id: int | None = None,
    origem_id: int | None = None,
    valor: Annotated[float | None, Field(ge=0)] = None,
    receita_pontual: bool | None = None,
    dores: str | None = None,
    comentarios: str | None = None,
    data_recebimento: date | None = None,
) -> dict:
    """Edita dados cadastrais de uma oportunidade. Só os campos informados mudam;
    não é possível apagar um campo por aqui. Etapa, qualificação e fechamento têm
    ferramentas próprias (mover_etapa, atualizar_qualificacao, marcar_*)."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "atualizar_oportunidade", escrita=True, argumentos=argumentos, opo_id=oportunidade_id) as s:
        obter_oportunidade_ativa(s, oportunidade_id)
        mapa = {
            "opoTitulo": titulo,
            "opoNomeContato": contato,
            "opoEmpresaContato": empresa,
            "opoEmail": email,
            "opoTelefone": telefone,
            "opoSolucao": solucao,
            "opoProId": produto_id,
            "opoUsuResponsavelId": responsavel_id,
            "opoCcoId": origem_id,
            "opoValorOportunidade": valor,
            "opoReceitaPontual": receita_pontual,
            "opoDoresMotivadores": dores,
            "opoComentarios": comentarios,
            "opoDataRecebimento": data_recebimento,
        }
        campos = {k: v for k, v in mapa.items() if v is not None}
        if not campos:
            raise BadRequestError("Nenhum campo para atualizar.")
        if produto_id is not None:
            validar_produto(s, produto_id)
        if responsavel_id is not None:
            validar_responsavel(s, responsavel_id)
        if origem_id is not None:
            validar_origem(s, origem_id)
        atualizada = oportunidade_service.update_oportunidade(
            s.db, oportunidade_id, OportunidadeUpdate(**campos), s.empId
        )
        return responder_oportunidade(s, atualizada)
