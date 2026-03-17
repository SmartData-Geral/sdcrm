from __future__ import annotations

from datetime import datetime, timezone
import re
import secrets
from typing import Optional
from urllib.parse import quote_plus

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import BadRequestError, NotFoundError
from ..models.oportunidade import Oportunidade
from ..models.empresa import Empresa
from ..models.proposta import Proposta
from ..models.proposta_bloco import PropostaBloco
from ..models.proposta_bloco_padrao import PropostaBlocoPadrao
from ..models.proposta_evento import PropostaEvento
from ..models.proposta_template import PropostaTemplate
from ..models.proposta_versao import PropostaVersao
from ..models.usuario import Usuario
from ..schemas.proposta import (
    PropostaBlocoCreate,
    PropostaBlocoPadraoCreate,
    PropostaBlocoPadraoListResponse,
    PropostaBlocoPadraoResponse,
    PropostaBlocoPadraoUpdate,
    PropostaBlocoListResponse,
    PropostaBlocoResponse,
    PropostaBlocoUpdate,
    PropostaCreate,
    PropostaEventoListResponse,
    PropostaEventoResponse,
    PropostaListResponse,
    PropostaPublicaResumoResponse,
    PropostaResponse,
    PropostaTemplateCreate,
    PropostaTemplateListResponse,
    PropostaTemplateResponse,
    PropostaTemplateUpdate,
    PropostaUpdate,
    PropostaVersaoCreate,
    PropostaVersaoListResponse,
    PropostaVersaoResponse,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_public_token() -> str:
    return secrets.token_urlsafe(24)


def _default_config(tipo: str, template: PropostaTemplate | None = None) -> dict:
    base = {
        "hero": {
            "titulo": "Proposta Smart Data",
            "subtitulo": "Transformacao digital orientada por dados",
        },
        "apresentacao": {
            "titulo": "Contexto",
            "texto": "Estruturamos uma proposta objetiva, visual e adaptada ao seu momento.",
        },
        "metodologia": {
            "titulo": "Por que escolher a Smart Data",
            "subtitulo": "Soluções pensadas para gerar eficiência, integração e resultado real para a sua operação.",
            "itens": [
                {
                    "titulo": "Experiência multissetorial",
                    "descricao": "Já automatizamos rotinas em mais de 15 segmentos, entendendo a fundo os desafios de cada tipo de operação.",
                    "icone": "experiencia",
                    "ordem": 1,
                },
                {
                    "titulo": "Soluções personalizadas",
                    "descricao": "Desenvolvemos sistemas sob medida para o seu processo, sem depender de planilhas genéricas.",
                    "icone": "personalizacao",
                    "ordem": 2,
                },
                {
                    "titulo": "Integrações completas",
                    "descricao": "Conectamos seu CRM, ERP e demais sistemas em um fluxo único de dados, reduzindo retrabalho.",
                    "icone": "integracoes",
                    "ordem": 3,
                },
                {
                    "titulo": "IA e automação",
                    "descricao": "Aplicamos inteligência artificial e automações inteligentes para reduzir tarefas operacionais e acelerar decisões.",
                    "icone": "ia_automacao",
                    "ordem": 4,
                },
            ],
        },
        "clientes": {
            "titulo": "Clientes",
            "subtitulo": "Empresas que escolheram dados e processo para crescer",
            "imagemUrl": None,
        },
        "cta_final": {
            "titulo": "Vamos colocar isso em prática?",
            "texto": "Clique em aceitar proposta ou fale diretamente no WhatsApp.",
        },
        "escopo_inicial": {
            "visivel": True,
            "titulo": "Fases do projeto",
            "subtitulo": "Detalhamento dos itens da proposta",
            "cards": [
                {
                    "titulo": "Escopo inicial",
                    "subtitulo": "Primeiro ciclo",
                    "itens": ["Diagnostico", "Plano de acao", "Setup inicial"],
                }
            ],
        },
        "valores_projeto": {
            "visivel": tipo in {"projeto", "hibrida"},
            "setup": {"visivel": True, "label": "Setup", "valor": "", "complemento": ""},
            "prazo": {"visivel": True, "label": "Prazo", "valor": "", "complemento": ""},
            "garantia": {"visivel": False, "label": "Garantia", "valor": "", "complemento": ""},
            "manutencao_mensal": {"visivel": False, "label": "Manutencao mensal", "valor": "", "complemento": ""},
            "melhorias_opcionais": {"visivel": False, "label": "Melhorias opcionais", "valor": "", "complemento": ""},
        },
        "valores_planos": {
            "visivel": tipo in {"planos", "hibrida"},
            "planos": [
                {
                    "nome": "Start",
                    "subtitulo": "",
                    "destaque": False,
                    "tema": "padrao",
                    "beneficios": ["Beneficio 1", "Beneficio 2"],
                    "valor": "",
                    "complemento_valor": "/mes",
                    "observacao": "",
                },
                {
                    "nome": "Smart",
                    "subtitulo": "",
                    "destaque": True,
                    "tema": "destaque",
                    "beneficios": ["Beneficio 1", "Beneficio 2", "Beneficio 3"],
                    "valor": "",
                    "complemento_valor": "/mes",
                    "observacao": "",
                },
                {
                    "nome": "Pro",
                    "subtitulo": "",
                    "destaque": False,
                    "tema": "padrao",
                    "beneficios": ["Beneficio 1", "Beneficio 2", "Beneficio 3", "Beneficio 4"],
                    "valor": "",
                    "complemento_valor": "/mes",
                    "observacao": "",
                },
            ],
        },
        "visibilidade": {
            "hero": True,
            "apresentacao": True,
            "metodologia": True,
            "escopo_inicial": True,
            "valores_projeto": tipo in {"projeto", "hibrida"},
            "valores_planos": tipo in {"planos", "hibrida"},
            "clientes": True,
            "cta_final": True,
        },
    }
    if template and template.ptlConfigJson:
        merged = dict(base)
        merged.update(template.ptlConfigJson)
        return merged
    return base


def _default_blocos(config: dict) -> list[dict]:
    return [
        {"pblTipo": "hero", "pblTitulo": "Hero", "pblSubtitulo": None, "pblOrdem": 1, "pblVisivel": True, "pblDadosJson": config.get("hero")},
        {
            "pblTipo": "apresentacao",
            "pblTitulo": "Apresentacao",
            "pblSubtitulo": None,
            "pblOrdem": 2,
            "pblVisivel": True,
            "pblDadosJson": config.get("apresentacao"),
        },
        {
            "pblTipo": "metodologia",
            "pblTitulo": "Metodologia",
            "pblSubtitulo": None,
            "pblOrdem": 3,
            "pblVisivel": True,
            "pblDadosJson": config.get("metodologia"),
        },
        {
            "pblTipo": "escopo_inicial",
            "pblTitulo": "Escopo Inicial",
            "pblSubtitulo": None,
            "pblOrdem": 4,
            "pblVisivel": bool(config.get("visibilidade", {}).get("escopo_inicial", True)),
            "pblDadosJson": config.get("escopo_inicial"),
        },
        {
            "pblTipo": "valores_projeto",
            "pblTitulo": "Valores Projeto",
            "pblSubtitulo": None,
            "pblOrdem": 5,
            "pblVisivel": bool(config.get("visibilidade", {}).get("valores_projeto", False)),
            "pblDadosJson": config.get("valores_projeto"),
        },
        {
            "pblTipo": "valores_planos",
            "pblTitulo": "Valores Planos",
            "pblSubtitulo": None,
            "pblOrdem": 6,
            "pblVisivel": bool(config.get("visibilidade", {}).get("valores_planos", False)),
            "pblDadosJson": config.get("valores_planos"),
        },
        {
            "pblTipo": "clientes",
            "pblTitulo": "Clientes",
            "pblSubtitulo": None,
            "pblOrdem": 7,
            "pblVisivel": True,
            "pblDadosJson": config.get("clientes"),
        },
        {
            "pblTipo": "cta_final",
            "pblTitulo": "CTA",
            "pblSubtitulo": None,
            "pblOrdem": 8,
            "pblVisivel": True,
            "pblDadosJson": config.get("cta_final"),
        },
    ]


def _get_responsavel_whatsapp(db: Session, proposta: Proposta) -> str | None:
    if proposta.prpWhatsappContato:
        return proposta.prpWhatsappContato
    if proposta.prpUsuResponsavelId is None:
        return None
    usu = db.get(Usuario, proposta.prpUsuResponsavelId)
    return usu.usuWhatsapp if usu else None


def _get_blocos_padroes_para_proposta(db: Session, proposta: Proposta) -> list[dict]:
    stmt = (
        select(PropostaBlocoPadrao)
        .where(
            PropostaBlocoPadrao.pbpEmpId == proposta.prpEmpId,
            PropostaBlocoPadrao.pbpAtivo.is_(True),
            PropostaBlocoPadrao.pbpTipo.isnot(None),
        )
        .order_by(PropostaBlocoPadrao.pbpOrdem.asc(), PropostaBlocoPadrao.pbpId.asc())
    )
    if proposta.prpTplId:
        stmt = stmt.where(
            (PropostaBlocoPadrao.pbpPtlId == proposta.prpTplId) | (PropostaBlocoPadrao.pbpPtlId.is_(None))
        )
    else:
        stmt = stmt.where(PropostaBlocoPadrao.pbpPtlId.is_(None))
    rows = db.scalars(stmt).all()
    return [
        {
            "pblTipo": row.pbpTipo,
            "pblTitulo": row.pbpTitulo,
            "pblSubtitulo": row.pbpSubtitulo,
            "pblOrdem": row.pbpOrdem,
            "pblVisivel": row.pbpVisivel,
            "pblDadosJson": row.pbpDadosJson,
        }
        for row in rows
    ]


def _normalize_whatsapp_number(number: str | None) -> str | None:
    if not number:
        return None
    digits = re.sub(r"\D+", "", number)
    return digits or None


def _format_apresentacao_html(texto: str) -> str:
    """Converte texto da apresentação em HTML com parágrafos e bullets."""
    if not texto or not str(texto).strip():
        return ""
    raw = str(texto).strip()
    parts = []
    for block in raw.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        bullet_lines = [ln[2:].strip() if ln.startswith("- ") else None for ln in lines]
        if all(b is not None for b in bullet_lines):
            parts.append("<ul class=\"bullets\">" + "".join(f"<li>{b}</li>" for b in bullet_lines) + "</ul>")
        else:
            parts.append(f"<p class=\"section__lead-p\">{block.replace(chr(10), '<br>')}</p>")
    return "".join(parts)


def _method_step_html(num: int, item: object) -> str:
    """Gera HTML de uma etapa da metodologia (número, título, descrição opcional)."""
    raw = str(item) if item else ""
    if "\n" in raw:
        titulo, desc = raw.split("\n", 1)
        titulo, desc = titulo.strip(), desc.strip()
    else:
        titulo, desc = raw.strip(), ""
    desc_html = f"<p class=\"method-step__desc\">{desc}</p>" if desc else ""
    return f'<div class="method-step" style="transition: all .2s ease;"><span class="method-step__num">{num}</span><div class="method-step__body"><span class="method-step__text">{titulo}</span>{desc_html}</div></div>'


def _differential_icon_symbol(key: str | None) -> str:
    raw = (key or "").strip().lower()
    if not raw:
        return "◆"
    mapping = {
        "experiencia": "★",
        "experiência": "★",
        "personalizacao": "⚙",
        "personalização": "⚙",
        "integracoes": "🔗",
        "integrações": "🔗",
        "ia_automacao": "⚡",
        "ia e automacao": "⚡",
        "ia e automação": "⚡",
        "ia": "⚡",
        "automacao": "⚡",
        "automação": "⚡",
    }
    return mapping.get(raw, "◆")


def _render_public_html(proposta: Proposta, whatsapp_number: str | None, empresa_logo_url: str | None = None) -> str:
    cfg = proposta.prpJsonConfiguracao or {}
    hero = cfg.get("hero") or {}
    apresentacao = cfg.get("apresentacao") or {}
    metodologia = cfg.get("metodologia") or cfg.get("diferenciais") or {}
    escopo = cfg.get("escopo_inicial") or {}
    valores_projeto = cfg.get("valores_projeto") or {}
    valores_planos = cfg.get("valores_planos") or {}
    clientes = cfg.get("clientes") or {}
    cta = cfg.get("cta_final") or {}
    vis = cfg.get("visibilidade") or {}
    tipo = (proposta.prpTipo or "").strip().lower()
    is_hibrida = tipo == "hibrida"
    message = quote_plus(f"Olá! Quero falar sobre a proposta: {proposta.prpTitulo}")
    wpp_link = f"https://wa.me/{whatsapp_number}?text={message}" if whatsapp_number else "#"

    list_planos = valores_planos.get("planos", []) or []
    has_planos = len(list_planos) > 0
    show_planos = vis.get("valores_planos", False) or has_planos
    show_projeto = (tipo != "planos") and vis.get("valores_projeto", False)

    plan_cards = "".join(
        [
            f"""
            <div class="plan-card {'destaque' if p.get('destaque') else ''}" style="transition: all .2s ease;">
              {('<span class="plan-card__badge">Plano recomendado</span>' if p.get('destaque') else '')}
              <h4 class="plan-card__nome">{p.get('nome', 'Plano')}</h4>
              <p class="plan-card__sub">{p.get('subtitulo', '')}</p>
              <ul class="plan-card__beneficios">{"".join([f'<li><span class="benefit-icon">✓</span>{item}</li>' for item in (p.get("beneficios") or [])])}</ul>
              <div class="plan-card__preco">{p.get('valor', '')}<small>{p.get('complemento_valor', '')}</small></div>
              <p class="plan-card__inclui">{p.get('observacao', '') or 'Inclui desenvolvimento contínuo, suporte técnico e melhorias.'}</p>
              <a class="btn btn-primary plan-card__cta" href="{wpp_link}" target="_blank" rel="noopener">Falar no WhatsApp</a>
            </div>
            """
            for p in list_planos
        ]
    )
    escopo_cards = "".join(
        [
            f"""
            <article class="scope-card scope-card--phase" style="transition: all .2s ease;">
              <h4 class="scope-card__titulo">{card.get('titulo', '')}</h4>
              <p class="scope-card__subtitulo">{card.get('subtitulo', '')}</p>
              <ul class="scope-card__itens">{"".join([f"<li>{item}</li>" for item in card.get("itens", [])])}</ul>
            </article>
            """
            for card in escopo.get("cards", [])
        ]
    )
    projeto_values = [
        ("setup", valores_projeto.get("setup", {})),
        ("prazo", valores_projeto.get("prazo", {})),
        ("garantia", valores_projeto.get("garantia", {})),
        ("manutencao_mensal", valores_projeto.get("manutencao_mensal", {})),
        ("melhorias_opcionais", valores_projeto.get("melhorias_opcionais", {})),
    ]
    setup_data = valores_projeto.get("setup", {}) or {}
    has_setup = bool(setup_data.get("visivel"))
    outros_projeto = [v for (k, v) in projeto_values if k != "setup" and v.get("visivel")]
    projeto_cards = "".join(
        [
            f'<div class="project-value-card" style="transition: all .2s ease;"><span class="project-value-card__label">{v.get("label", "")}</span><span class="project-value-card__valor">{v.get("valor", "")} {v.get("complemento", "")}</span></div>'
            for _, v in projeto_values
            if v.get("visivel")
        ]
    )
    investimento_inicial_html = ""
    if has_setup:
        valor_setup = f"{setup_data.get('valor', '')} {setup_data.get('complemento', '')}".strip()
        investimento_inicial_html = f'<div class="project-invest-block"><h3 class="project-invest__titulo">Investimento inicial</h3><p class="project-invest__valor">{valor_setup}</p></div>'
    projeto_secondary_html = ""
    if outros_projeto:
        projeto_secondary_html = "<div class=\"project-values-grid project-values-grid--secondary\">" + "".join(
            f'<div class="project-value-card"><span class="project-value-card__label">{v.get("label", "")}</span><span class="project-value-card__valor">{v.get("valor", "")} {v.get("complemento", "")}</span></div>'
            for v in outros_projeto
        ) + "</div>"

    metodologia_itens_raw = metodologia.get("itens", []) or []
    metodologia_itens: list[dict] = []
    for idx, raw_item in enumerate(metodologia_itens_raw):
        if isinstance(raw_item, dict):
            metodologia_itens.append(raw_item)
        elif raw_item is not None:
            metodologia_itens.append(
                {
                    "titulo": str(raw_item),
                    "descricao": "",
                    "icone": None,
                    "ordem": idx + 1,
                }
            )
    clientes_img_url = str(clientes.get("imagemUrl") or "").strip()

    cliente_nome = (proposta.prpNomeContato or "").strip()
    default_hero_title = f"Proposta Smart Data{(' | ' + cliente_nome) if cliente_nome else ''}"
    hero_title = str(hero.get("titulo") or default_hero_title or proposta.prpTitulo)
    hero_sub = str(hero.get("subtitulo", ""))
    hero_valor = str(hero.get("frase_valor") or "").strip()
    brand_html = (
        f'<div class="hero__brand-row">'
        f'<img src="{empresa_logo_url}" alt="Logo da empresa" class="hero__logo" />'
        f'</div>'
        if empresa_logo_url
        else '<p class="hero__brand-text">SMART DATA · PROPOSTA COMERCIAL</p>'
    )
    hero_section = (
        f'<section class="hero">'
        f'<div class="hero__overlay"></div>'
        f'<div class="hero__inner">'
        f'{brand_html}'
        f'<h1 class="hero__titulo">{hero_title}</h1>'
        f'<div class="hero__row">'
        f'<p class="hero__subtitulo">{hero_sub}</p>'
        f'<div class="hero__cta">'
        f'<a class="btn btn-whatsapp" href="{wpp_link}" target="_blank" rel="noopener">Falar no WhatsApp</a>'
        f'<button type="button" class="btn btn-primary btn-aceitar">Aceitar proposta</button>'
        f'</div>'
        f'</div>'
        f'{"<p class=\"hero__valor\">" + hero_valor + "</p>" if hero_valor else ""}'
        f"</div></section>"
        if vis.get("hero", True)
        else ""
    )
    apres_titulo = str(apresentacao.get("titulo", "Contexto") or "Contexto")
    apres_badge = str(apresentacao.get("badge") or "").strip()
    apres_texto_raw = str(apresentacao.get("texto", "") or "")
    apres_body = _format_apresentacao_html(apres_texto_raw)
    apres_content = apres_body if apres_body else f'<p class="section__lead-p">{apres_texto_raw}</p>'
    apres_pontos = [str(p).strip() for p in (apresentacao.get("pontos") or []) if str(p).strip()]
    apres_list_html = ""
    if apres_pontos:
        apres_list_html = "<ul class=\"context-list\">" + "".join(
            f'<li><span class="benefit-icon">✓</span>{p}</li>' for p in apres_pontos
        ) + "</ul>"
    apres_img_url = str(apresentacao.get("imagemUrl") or "").strip()
    badge_html = f'<span class="context-badge">{apres_badge}</span>' if apres_badge else ""
    context_image_html = (
        f'<img src="{apres_img_url}" alt="Imagem ilustrativa" class="context-image" />'
        if apres_img_url
        else '<div class="context-image context-image--placeholder"></div>'
    )
    apres_section = (
        f'<section class="section section--alt section--context">'
        f'<div class="context-grid">'
        f'<div class="context-col context-col--text">'
        f'{badge_html}'
        f'<h2 class="section__titulo">{apres_titulo}</h2>'
        f'<div class="section__lead context-lead">{apres_content}</div>'
        f'{apres_list_html}'
        f'</div>'
        f'<div class="context-col context-col--image">'
        f'{context_image_html}'
        f'</div>'
        f"</div></section>"
        if vis.get("apresentacao", True)
        else ""
    )
    diff_titulo = str(metodologia.get("titulo") or "Por que escolher a Smart Data")
    diff_subtitulo = str(
        metodologia.get(
            "subtitulo",
            "Soluções pensadas para gerar eficiência, integração e resultado real para a sua operação.",
        )
        or ""
    )
    diff_cards_html = "".join(
        f"""
            <article class="diff-card" style="transition: all .2s ease;">
              <div class="diff-card__icon-wrap">
                <span class="diff-card__icon">{_differential_icon_symbol(str(item.get("icone")) if isinstance(item.get("icone"), str) else None)}</span>
              </div>
              <h3 class="diff-card__title">{str(item.get("titulo") or "Diferencial")}</h3>
              <p class="diff-card__desc">{str(item.get("descricao") or "")}</p>
            </article>
        """
        for item in metodologia_itens
    )
    metodologia_section = (
        f'<section class="section section--differentials"><div class="section__inner">'
        f'<h2 class="section__titulo">{diff_titulo}</h2>'
        f'<p class="section__subtitulo">{diff_subtitulo}</p>'
        f'<div class="diff-grid">{diff_cards_html}</div></div></section>'
        if vis.get("metodologia", True)
        else ""
    )
    escopo_titulo = str(escopo.get("titulo") or "Fases do projeto")
    escopo_subtitulo = str(escopo.get("subtitulo") or "Detalhamento dos itens da proposta")
    escopo_section = (
        f'<section class="section section--alt"><h2 class="section__titulo">{escopo_titulo}</h2>'
        f'<p class="section__subtitulo">{escopo_subtitulo}</p>'
        f'<div class="scope-grid">{escopo_cards}</div></section>'
        if vis.get("escopo_inicial", True)
        else ""
    )
    projeto_section_content = ""
    if has_setup:
        projeto_section_content = investimento_inicial_html + projeto_secondary_html
    else:
        projeto_section_content = f'<div class="project-values-grid">{projeto_cards}</div>'
    if is_hibrida and show_projeto:
        projeto_section = (
            f'<section class="section"><h2 class="hybrid-option-title">Projeto sob medida</h2>'
            f'{projeto_section_content}</section>'
        )
    elif show_projeto:
        projeto_section = (
            f'<section class="section"><h2 class="section__titulo">{str(valores_projeto.get("titulo") or "Investimento no projeto")}</h2>'
            f'<p class="section__subtitulo">Valores, prazos e condições</p>{projeto_section_content}</section>'
        )
    else:
        projeto_section = ""

    planos_titulo = str(valores_planos.get("titulo", "Planos de acompanhamento"))
    planos_subtitulo = str(valores_planos.get("subtitulo") or "Compare os planos e escolha o ideal para sua operação")
    planos_section_content = f'<div class="plan-grid">{plan_cards}</div>'
    if is_hibrida and show_planos:
        planos_section = (
            f'<section class="section section--alt section--pricing"><h2 class="hybrid-option-title">Planos recorrentes</h2>'
            f'<p class="section__subtitulo">{planos_subtitulo}</p>{planos_section_content}</section>'
        )
    elif show_planos:
        planos_section = (
            f'<section class="section section--alt section--pricing"><h2 class="section__titulo">{planos_titulo}</h2>'
            f'<p class="section__subtitulo">{planos_subtitulo}</p>{planos_section_content}</section>'
        )
    else:
        planos_section = ""
    clientes_titulo = str(clientes.get("titulo", "Quem já confia na Smart Data"))
    clientes_subtitulo = str(
        clientes.get("subtitulo") or "Empresas que escolheram dados e processo para crescer"
    )
    clientes_image_html = (
        f'<div class="clientes-image-wrap"><img src="{clientes_img_url}" alt="Clientes Smart Data" class="clientes-image" /></div>'
        if clientes_img_url
        else '<div class="clientes-image-wrap clientes-image--placeholder"></div>'
    )
    clientes_section = (
        f'<section class="section">'
        f'<h2 class="section__titulo">{clientes_titulo}</h2>'
        f'<p class="section__subtitulo">{clientes_subtitulo}</p>'
        f'{clientes_image_html}'
        f"</section>"
        if vis.get("clientes", True)
        else ""
    )
    cta_titulo = str(cta.get("titulo", "Vamos colocar isso em prática?"))
    cta_texto = str(cta.get("texto") or "Fale no WhatsApp ou aceite abaixo. Estamos prontos para começar.")
    cta_section = (
        f'<section class="section cta-final">'
        f'<h2 class="cta-final__titulo">{cta_titulo}</h2>'
        f'<p class="cta-final__texto">{cta_texto}</p>'
        f'<div class="cta-final__btns">'
        f'<a class="btn btn-whatsapp" href="{wpp_link}" target="_blank" rel="noopener">Falar no WhatsApp</a>'
        f'<button type="button" class="btn btn-primary btn-aceitar">Aceitar proposta</button>'
        f"</div></section>"
        if vis.get("cta_final", True)
        else ""
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{proposta.prpTitulo}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; background: #e2e8f0; color: #0f172a; line-height: 1.5; -webkit-font-smoothing: antialiased; }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 32px 40px 56px; }}
    .hero {{ position: relative; background: linear-gradient(145deg, #0f172a 0%, #1e3a5f 42%, #1d4ed8 100%); color: #fff; border-radius: 24px; padding: 40px 40px 28px; margin-bottom: 28px; text-align: left; box-shadow: 0 24px 56px rgba(15, 23, 42, 0.28); overflow: hidden; }}
    .hero__overlay {{ position: absolute; inset: 0; background: rgba(0,0,0,.1); pointer-events: none; }}
    .hero__inner {{ position: relative; z-index: 1; max-width: 720px; margin: 0; display: flex; flex-direction: column; gap: 10px; }}
    .hero__brand-row {{ display: flex; align-items: center; justify-content: flex-start; gap: 0.85rem; margin: 0 0 20px; }}
    .hero__logo {{ max-height: 56px; max-width: 220px; object-fit: contain; display: block; }}
    .hero__brand-text {{ margin: 0; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; opacity: 0.95; text-shadow: 0 1px 2px rgba(0,0,0,.2); }}
    .hero__titulo {{ margin: 0; font-size: 34px; font-weight: 800; line-height: 1.2; letter-spacing: -0.02em; text-shadow: 0 2px 4px rgba(0,0,0,.2); }}
    .hero__row {{ display: flex; align-items: center; gap: 12px; margin-top: 8px; }}
    .hero__subtitulo {{ margin: 0; font-size: 1.02rem; opacity: 0.95; line-height: 1.4; flex: 1; }}
    .hero__valor {{ margin: 4px 0 20px; font-size: 0.95rem; opacity: 0.9; line-height: 1.45; }}
    .hero__cta {{ display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end; align-items: center; }}
    .section {{ background: #fff; border-radius: 18px; padding: 32px 28px; margin-bottom: 32px; box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06); border: 1px solid rgba(226, 232, 240, 0.9); transition: box-shadow .2s ease; }}
    .section:hover {{ box-shadow: 0 8px 32px rgba(15, 23, 42, 0.08); }}
    .section--alt {{ background: #f8fafc; border-color: #e2e8f0; }}
    .section--context {{ padding: 32px 30px; }}
    .section--pricing {{ padding: 40px 28px; }}
    .section__inner {{ max-width: 100%; }}
    .section__inner--read {{ max-width: 58ch; }}
    .section__titulo {{ margin: 0 0 10px; font-size: 1.5rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em; }}
    .section__subtitulo {{ margin: 0 0 24px; font-size: 0.95rem; color: #64748b; line-height: 1.4; }}
    .section__lead {{ margin: 0; font-size: 1.05rem; color: #334155; line-height: 1.7; }}
    .section__lead-p {{ margin: 0 0 1em; }}
    .section__lead-p:last-child {{ margin-bottom: 0; }}
    .bullets {{ margin: 0.5em 0 1em; padding-left: 1.4rem; list-style: none; }}
    .bullets li {{ position: relative; margin-bottom: 0.35em; }}
    .bullets li::before {{ content: "•"; position: absolute; left: -1rem; color: #1d4ed8; font-weight: 700; }}
    .highlight {{ background: linear-gradient(120deg, rgba(29,78,216,.08) 0%, transparent 100%); padding: 0 4px; border-radius: 4px; }}
    .callout {{ border-left: 4px solid #1d4ed8; padding-left: 1rem; margin: 1em 0; color: #334155; }}
    .context-grid {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1.1fr); gap: 28px; align-items: center; }}
    .context-col--text {{ display: flex; flex-direction: column; gap: 12px; }}
    .context-col--image {{ display: flex; justify-content: center; }}
    .context-badge {{ display: inline-flex; align-items: center; justify-content: center; padding: 4px 10px; border-radius: 999px; background: #f97316; color: #fff; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; width: fit-content; }}
    .context-lead {{ margin-top: 4px; font-size: 0.94rem; line-height: 1.62; }}
    .context-list {{ margin: 4px 0 0; padding-left: 0; list-style: none; font-size: 0.84rem; color: #475569; line-height: 1.55; display: flex; flex-direction: column; gap: 6px; }}
    .context-list li {{ display: flex; align-items: flex-start; gap: 8px; }}
    .context-image {{ width: 100%; max-width: 360px; border-radius: 18px; object-fit: cover; min-height: 200px; background-size: cover; background-position: center; }}
    .context-image--placeholder {{ background: radial-gradient(circle at top left, #1d4ed8, #0f172a); }}
    .scope-grid {{ display: grid; gap: 24px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }}
    .scope-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 28px; transition: all .2s ease; box-shadow: 0 2px 16px rgba(15, 23, 42, 0.04); }}
    .scope-card:hover {{ box-shadow: 0 10px 32px rgba(15, 23, 42, 0.1); border-color: #cbd5e1; }}
    .scope-card--phase {{ padding: 30px; }}
    .scope-card__titulo {{ margin: 0 0 10px; font-size: 1.12rem; font-weight: 700; color: #0f172a; }}
    .scope-card__subtitulo {{ margin: 0 0 16px; font-size: 0.9rem; color: #64748b; line-height: 1.45; }}
    .scope-card__itens {{ margin: 0; padding-left: 1.25rem; font-size: 0.92rem; color: #475569; line-height: 1.65; }}
    .section--differentials {{ padding: 40px 30px; }}
    .section--differentials .section__subtitulo {{ margin-bottom: 22px; }}
    .diff-grid {{ display: grid; gap: 20px; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); margin-top: 12px; }}
    .diff-card {{ background: #fff; border-radius: 18px; border: 1px solid #e2e8f0; padding: 22px 20px; box-shadow: 0 6px 22px rgba(15, 23, 42, 0.06); display: flex; flex-direction: column; gap: 8px; }}
    .diff-card__icon-wrap {{ width: 44px; height: 44px; border-radius: 14px; background: linear-gradient(145deg, #fee2e2, #fef3c7); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 4px; }}
    .diff-card__icon {{ font-size: 1.35rem; }}
    .diff-card__title {{ margin: 0; font-size: 1.02rem; font-weight: 700; color: #0f172a; }}
    .diff-card__desc {{ margin: 0; font-size: 0.9rem; color: #64748b; line-height: 1.55; }}
    .project-invest-block {{ background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%); color: #fff; border-radius: 18px; padding: 32px; margin-bottom: 24px; text-align: center; }}
    .project-invest__titulo {{ margin: 0 0 8px; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.9; }}
    .project-invest__valor {{ margin: 0; font-size: 2.25rem; font-weight: 800; }}
    .project-values-grid {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); margin-top: 16px; }}
    .project-values-grid--secondary {{ margin-top: 0; }}
    .project-value-card {{ background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 6px; }}
    .project-value-card__label {{ font-size: 0.8rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.03em; }}
    .project-value-card__valor {{ font-size: 1.2rem; font-weight: 700; color: #0f172a; }}
    .plan-grid {{ display: grid; gap: 24px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); margin-top: 28px; align-items: stretch; }}
    .plan-card {{ position: relative; background: #fff; border: 2px solid #e2e8f0; border-radius: 20px; padding: 28px; display: flex; flex-direction: column; transition: all .2s ease; min-height: 420px; }}
    .plan-card:hover {{ border-color: #cbd5e1; box-shadow: 0 10px 32px rgba(15, 23, 42, 0.08); }}
    .plan-card.destaque {{ border-color: #1d4ed8; box-shadow: 0 16px 48px rgba(29, 78, 216, 0.2); background: linear-gradient(180deg, #fff 0%, #f0f7ff 100%); transform: scale(1.02); }}
    .plan-card.destaque:hover {{ box-shadow: 0 20px 52px rgba(29, 78, 216, 0.24); }}
    .plan-card__badge {{ position: absolute; top: 16px; right: 16px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; background: #1d4ed8; color: #fff; padding: 6px 12px; border-radius: 20px; }}
    .plan-card__nome {{ margin: 0 0 8px; font-size: 1.3rem; font-weight: 700; color: #0f172a; }}
    .plan-card__sub {{ margin: 0 0 18px; font-size: 0.88rem; color: #64748b; }}
    .plan-card__beneficios {{ margin: 0 0 20px; padding-left: 0; list-style: none; font-size: 0.92rem; color: #475569; line-height: 1.65; flex: 1; }}
    .plan-card__beneficios li {{ display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px; }}
    .benefit-icon {{ color: #22c55e; font-weight: 700; flex-shrink: 0; }}
    .plan-card__preco {{ font-size: 2.1rem; font-weight: 800; color: #1d4ed8; margin-bottom: 8px; }}
    .plan-card__preco small {{ font-size: 0.88rem; font-weight: 500; color: #64748b; margin-left: 4px; }}
    .plan-card__inclui {{ margin: 0 0 24px; font-size: 0.82rem; color: #64748b; line-height: 1.45; }}
    .plan-card__cta {{ margin-top: auto; padding-top: 8px; text-align: center; }}
    .hybrid-option-title {{ margin: 0 0 10px; font-size: 1.25rem; font-weight: 700; color: #1d4ed8; }}
    .clientes-image-wrap {{ margin-top: 16px; border-radius: 18px; overflow: hidden; box-shadow: 0 14px 40px rgba(15, 23, 42, 0.18); background: #ffffff; padding: 12px 16px; }}
    .clientes-image {{ display: block; width: 100%; height: auto; object-fit: contain; }}
    .clientes-image--placeholder {{ margin-top: 16px; height: 260px; border-radius: 18px; background: radial-gradient(circle at top left, #1d4ed8, #0f172a); box-shadow: 0 14px 40px rgba(15, 23, 42, 0.18); }}
    .cta-final {{ text-align: center; padding: 52px 32px; background: linear-gradient(145deg, #0f172a 0%, #1e3a5f 100%); color: #fff; border: none; border-radius: 20px; }}
    .cta-final__titulo {{ margin: 0 0 14px; font-size: 1.75rem; font-weight: 800; color: #fff; letter-spacing: -0.02em; }}
    .cta-final__texto {{ margin: 0 0 32px; opacity: 0.94; font-size: 1.05rem; max-width: 440px; margin-left: auto; margin-right: auto; line-height: 1.55; }}
    .cta-final__btns {{ display: flex; flex-wrap: wrap; gap: 16px; justify-content: center; }}
    .btn {{ display: inline-flex; align-items: center; justify-content: center; padding: 6px 14px; border-radius: 999px; font-weight: 500; font-size: 0.78rem; text-decoration: none; border: none; cursor: pointer; transition: all .2s ease; }}
    .btn:active {{ transform: scale(0.98); }}
    .btn:hover {{ filter: brightness(1.06); }}
    .btn-primary {{ background: #2563eb; color: #fff; }}
    .btn-primary:hover {{ background: #1d4ed8; }}
    .btn-whatsapp {{ background: #22c55e; color: #fff; }}
    .btn-whatsapp:hover {{ background: #16a34a; }}
    .proposal-footer {{ margin-top: 8px; border-radius: 22px; overflow: hidden; background: radial-gradient(circle at top left, #020617, #020617 40%, #020617 100%); color: #e2e8f0; box-shadow: 0 -6px 30px rgba(15,23,42,0.55); }}
    .proposal-footer-inner {{ padding: 22px 32px 26px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; font-size: 0.86rem; }}
    .proposal-footer-left {{ display: flex; flex-direction: column; gap: 4px; }}
    .proposal-footer-brand {{ font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; font-size: 0.7rem; color: #9ca3af; }}
    .proposal-footer-main {{ font-weight: 500; color: #e5e7eb; }}
    .proposal-footer-right {{ display: flex; flex-wrap: wrap; gap: 14px; }}
    .proposal-footer-link {{ display: inline-flex; align-items: center; gap: 6px; color: #cbd5f5; text-decoration: none; opacity: 0.9; }}
    .proposal-footer-link svg {{ width: 15px; height: 15px; stroke-width: 1.8; }}
    .proposal-footer-link:hover {{ opacity: 1; color: #fff; }}
    .proposal-footer-bottom-bar {{ height: 3px; background: linear-gradient(90deg, #1d4ed8, #004aad, #22c55e); }}
    @media (min-width: 900px) {{
      .plan-grid {{ grid-template-columns: repeat(3, 1fr); gap: 24px; }}
      .plan-card {{ min-height: 440px; }}
      .scope-grid {{ grid-template-columns: repeat(3, 1fr); }}
    }}
    @media (max-width: 899px) {{
      .method-step:not(:last-child)::after {{ display: none; }}
    }}
    @media (max-width: 899px) and (min-width: 641px) {{
      .plan-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .scope-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    @media (max-width: 640px) {{
      .wrap {{ padding: 18px 16px 36px; }}
      .hero {{ padding: 44px 22px 40px; border-radius: 18px; margin-bottom: 28px; text-align: left; }}
      .hero__inner {{ max-width: 100%; }}
      .hero__logo {{ max-height: 40px; max-width: 180px; }}
      .hero__titulo {{ font-size: 26px; }}
      .hero__subtitulo {{ font-size: 1rem; }}
      .hero__valor {{ margin-bottom: 28px; }}
      .hero__cta {{ flex-direction: column; gap: 14px; }}
      .hero__cta .btn {{ width: 100%; max-width: 280px; }}
      .section {{ padding: 24px 20px; margin-bottom: 24px; border-radius: 16px; }}
      .section--pricing {{ padding: 28px 20px; }}
      .context-grid {{ grid-template-columns: 1fr; }}
      .context-col--image {{ order: 2; }}
      .context-col--text {{ order: 1; }}
      .scope-grid {{ grid-template-columns: 1fr; }}
      .scope-card--phase {{ padding: 24px; }}
      .plan-grid {{ grid-template-columns: 1fr; }}
      .plan-card {{ min-height: 0; }}
      .plan-card.destaque {{ transform: none; }}
      .method-steps {{ flex-direction: column; gap: 16px; }}
      .method-step {{ flex: 1 1 auto; }}
      .method-step:not(:last-child)::after {{ display: none; }}
      .project-invest-block {{ padding: 24px 20px; }}
      .project-invest__valor {{ font-size: 1.75rem; }}
      .clientes-grid {{ grid-template-columns: 1fr; }}
      .cta-final {{ padding: 40px 22px; border-radius: 18px; }}
      .cta-final__titulo {{ font-size: 1.4rem; }}
      .cta-final__btns {{ flex-direction: column; }}
      .cta-final__btns .btn {{ width: 100%; max-width: 280px; margin: 0 auto; }}
      .proposal-footer-inner {{ padding: 18px 18px 20px; flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    {hero_section}
    {apres_section}
    {metodologia_section}
    {escopo_section}
    {projeto_section}
    {planos_section}
    {clientes_section}
    {cta_section}
    <footer class="proposal-footer">
      <div class="proposal-footer-inner">
        <div class="proposal-footer-left">
          <span class="proposal-footer-brand">SMART DATA · INTELIGÊNCIA PARA O SEU NEGÓCIO</span>
          <span class="proposal-footer-main">Soluções para alavancar a sua operação.</span>
        </div>
        <div class="proposal-footer-right">
          <a class="proposal-footer-link" href="mailto:comercial@smartdatabi.com.br">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <rect x="3" y="5" width="18" height="14" rx="2" ry="2"></rect>
              <polyline points="3,7 12,13 21,7"></polyline>
            </svg>
            <span>comercial@smartdatabi.com.br</span>
          </a>
          <a class="proposal-footer-link" href="tel:+5541998018834">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2 4.18 2 2 0 0 1 4.11 2h3A2 2 0 0 1 9.1 3.72a12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
            </svg>
            <span>(41) 99801-8834</span>
          </a>
          <span class="proposal-footer-link" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 12 8 12s8-6.75 8-12a8 8 0 0 0-8-8z"></path>
              <circle cx="12" cy="10" r="3"></circle>
            </svg>
            <span>Curitiba · PR</span>
          </span>
        </div>
      </div>
      <div class="proposal-footer-bottom-bar"></div>
    </footer>
  </div>
  <script>
    (function() {{
      async function post(path) {{
        await fetch(path, {{ method: "POST", headers: {{ "Content-Type": "application/json" }}, body: JSON.stringify({{}}) }});
      }}
      post(window.location.pathname + "/visualizacao");
      document.querySelectorAll(".btn-aceitar").forEach(function(btn) {{
        btn.addEventListener("click", async function() {{
          await post(window.location.pathname + "/aceite");
          alert("Proposta aceita com sucesso.");
        }});
      }});
    }})();
  </script>
</body>
</html>"""


def _get_oportunidade(db: Session, opo_id: int, company_id: Optional[int]) -> Oportunidade:
    stmt = select(Oportunidade).where(Oportunidade.opoId == opo_id)
    if company_id is not None:
        stmt = stmt.where(Oportunidade.opoEmpId == company_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Oportunidade não encontrada")
    return row


def _get_proposta(db: Session, prp_id: int, company_id: Optional[int]) -> Proposta:
    stmt = select(Proposta).where(Proposta.prpId == prp_id)
    if company_id is not None:
        stmt = stmt.where(Proposta.prpEmpId == company_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Proposta não encontrada")
    return row


def _get_template(db: Session, ptl_id: int, company_id: Optional[int]) -> PropostaTemplate:
    stmt = select(PropostaTemplate).where(PropostaTemplate.ptlId == ptl_id)
    if company_id is not None:
        stmt = stmt.where(PropostaTemplate.ptlEmpId == company_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Template de proposta não encontrado")
    return row


def _create_event(
    db: Session,
    proposta: Proposta,
    event_type: str,
    prv_id: int | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    dados: dict | None = None,
) -> PropostaEvento:
    event = PropostaEvento(
        pevEmpId=proposta.prpEmpId,
        pevPrpId=proposta.prpId,
        pevPrvId=prv_id,
        pevTipo=event_type,
        pevIp=ip,
        pevUserAgent=user_agent,
        pevDadosJson=dados,
        pevDataEvento=_utcnow(),
    )
    db.add(event)
    return event


def list_propostas(
    db: Session,
    company_id: Optional[int],
    oportunidade_id: int | None = None,
    status: str | None = None,
    tipo: str | None = None,
    responsavel_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PropostaListResponse:
    stmt = select(Proposta)
    if company_id is not None:
        stmt = stmt.where(Proposta.prpEmpId == company_id)
    if oportunidade_id is not None:
        stmt = stmt.where(Proposta.prpOpoId == oportunidade_id)
    if status:
        stmt = stmt.where(Proposta.prpStatus == status)
    if tipo:
        stmt = stmt.where(Proposta.prpTipo == tipo)
    if responsavel_id is not None:
        stmt = stmt.where(Proposta.prpUsuResponsavelId == responsavel_id)
    stmt = stmt.order_by(Proposta.prpDataCriacao.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return PropostaListResponse(
        items=[PropostaResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_propostas_oportunidade(db: Session, opo_id: int, company_id: Optional[int], page: int, page_size: int) -> PropostaListResponse:
    return list_propostas(
        db=db,
        company_id=company_id,
        oportunidade_id=opo_id,
        page=page,
        page_size=page_size,
    )


def get_proposta(db: Session, prp_id: int, company_id: Optional[int]) -> PropostaResponse:
    return PropostaResponse.model_validate(_get_proposta(db, prp_id, company_id))


def create_proposta(db: Session, data: PropostaCreate, company_id: Optional[int], usu_id: int) -> PropostaResponse:
    oportunidade = _get_oportunidade(db, data.prpOpoId, company_id)
    template = _get_template(db, data.prpTplId, company_id) if data.prpTplId else None
    responsavel_id = data.prpUsuResponsavelId or oportunidade.opoUsuResponsavelId
    responsavel = db.get(Usuario, responsavel_id) if responsavel_id else None
    config = data.prpJsonConfiguracao or _default_config(data.prpTipo, template)
    proposta = Proposta(
        prpEmpId=oportunidade.opoEmpId,
        prpOpoId=oportunidade.opoId,
        prpTplId=data.prpTplId,
        prpTitulo=data.prpTitulo,
        prpTipo=data.prpTipo,
        prpStatus="rascunho",
        prpTokenPublico=_new_public_token(),
        prpUsuCriadorId=usu_id,
        prpUsuEditorId=usu_id,
        prpUsuResponsavelId=responsavel_id,
        prpNomeContato=data.prpNomeContato or oportunidade.opoNomeContato,
        prpEmailContato=data.prpEmailContato or oportunidade.opoEmail,
        prpWhatsappContato=data.prpWhatsappContato or (responsavel.usuWhatsapp if responsavel else oportunidade.opoTelefone),
        prpObservacaoInterna=data.prpObservacaoInterna,
        prpJsonConfiguracao=config,
        prpHtmlRenderizado=None,
    )
    db.add(proposta)
    db.flush()
    blocos_base = _get_blocos_padroes_para_proposta(db, proposta)
    if not blocos_base:
        blocos_base = _default_blocos(config)
    for bloco in blocos_base:
        db.add(PropostaBloco(pblEmpId=proposta.prpEmpId, pblPrpId=proposta.prpId, **bloco))
    _create_event(db, proposta, "abertura_link", dados={"origem": "interno_criacao"})
    db.commit()
    db.refresh(proposta)
    return PropostaResponse.model_validate(proposta)


def update_proposta(db: Session, prp_id: int, data: PropostaUpdate, company_id: Optional[int], usu_id: int) -> PropostaResponse:
    proposta = _get_proposta(db, prp_id, company_id)
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(proposta, k, v)
    proposta.prpUsuEditorId = usu_id
    db.add(proposta)
    db.commit()
    db.refresh(proposta)
    return PropostaResponse.model_validate(proposta)


def arquivar_proposta(db: Session, prp_id: int, company_id: Optional[int], usu_id: int) -> PropostaResponse:
    proposta = _get_proposta(db, prp_id, company_id)
    proposta.prpStatus = "arquivada"
    proposta.prpUsuEditorId = usu_id
    db.add(proposta)
    db.commit()
    db.refresh(proposta)
    return PropostaResponse.model_validate(proposta)


def duplicar_proposta(db: Session, prp_id: int, company_id: Optional[int], usu_id: int) -> PropostaResponse:
    original = _get_proposta(db, prp_id, company_id)
    clone = Proposta(
        prpEmpId=original.prpEmpId,
        prpOpoId=original.prpOpoId,
        prpTplId=original.prpTplId,
        prpTitulo=f"{original.prpTitulo} (Cópia)",
        prpTipo=original.prpTipo,
        prpStatus="rascunho",
        prpTokenPublico=_new_public_token(),
        prpVersaoAtual=None,
        prpUsuCriadorId=usu_id,
        prpUsuEditorId=usu_id,
        prpUsuResponsavelId=original.prpUsuResponsavelId,
        prpNomeContato=original.prpNomeContato,
        prpEmailContato=original.prpEmailContato,
        prpWhatsappContato=original.prpWhatsappContato,
        prpObservacaoInterna=original.prpObservacaoInterna,
        prpJsonConfiguracao=original.prpJsonConfiguracao,
        prpHtmlRenderizado=original.prpHtmlRenderizado,
    )
    db.add(clone)
    db.flush()
    blocos = db.scalars(
        select(PropostaBloco).where(PropostaBloco.pblPrpId == original.prpId, PropostaBloco.pblAtivo.is_(True))
    ).all()
    for b in blocos:
        db.add(
            PropostaBloco(
                pblEmpId=clone.prpEmpId,
                pblPrpId=clone.prpId,
                pblTipo=b.pblTipo,
                pblTitulo=b.pblTitulo,
                pblSubtitulo=b.pblSubtitulo,
                pblOrdem=b.pblOrdem,
                pblVisivel=b.pblVisivel,
                pblDadosJson=b.pblDadosJson,
            )
        )
    db.commit()
    db.refresh(clone)
    return PropostaResponse.model_validate(clone)


def publicar_proposta(db: Session, prp_id: int, company_id: Optional[int], usu_id: int, forcar_nova_versao: bool = True) -> PropostaResponse:
    proposta = _get_proposta(db, prp_id, company_id)
    whatsapp_number = _normalize_whatsapp_number(_get_responsavel_whatsapp(db, proposta))
    empresa = db.get(Empresa, proposta.prpEmpId)
    logo_url = empresa.empLogoUrl if empresa else None  # type: ignore[attr-defined]
    html = _render_public_html(proposta, whatsapp_number, logo_url)
    proposta.prpHtmlRenderizado = html
    proposta.prpPublicadaEm = _utcnow()
    proposta.prpStatus = "publicada"
    proposta.prpUsuEditorId = usu_id

    next_num = 1
    if proposta.prpVersaoAtual:
        next_num = proposta.prpVersaoAtual + (1 if forcar_nova_versao else 0)
    elif not forcar_nova_versao:
        last = db.scalars(
            select(PropostaVersao)
            .where(PropostaVersao.prvPrpId == proposta.prpId)
            .order_by(PropostaVersao.prvNumero.desc())
            .limit(1)
        ).first()
        if last:
            next_num = last.prvNumero

    versao = db.scalars(
        select(PropostaVersao).where(PropostaVersao.prvPrpId == proposta.prpId, PropostaVersao.prvNumero == next_num)
    ).first()
    if versao is None:
        versao = PropostaVersao(
            prvEmpId=proposta.prpEmpId,
            prvPrpId=proposta.prpId,
            prvNumero=next_num,
            prvTitulo=proposta.prpTitulo,
            prvJsonSnapshot=proposta.prpJsonConfiguracao,
            prvHtmlSnapshot=html,
            prvPublicada=True,
            prvUsuId=usu_id,
            prvDataPublicacao=_utcnow(),
        )
    else:
        versao.prvTitulo = proposta.prpTitulo
        versao.prvJsonSnapshot = proposta.prpJsonConfiguracao
        versao.prvHtmlSnapshot = html
        versao.prvPublicada = True
        versao.prvUsuId = usu_id
        versao.prvDataPublicacao = _utcnow()
    proposta.prpVersaoAtual = next_num
    db.add(versao)
    db.flush()
    db.add(proposta)
    opo = db.get(Oportunidade, proposta.prpOpoId)
    if opo:
        opo.opoPropostaEnviada = True
        db.add(opo)
    _create_event(
        db=db,
        proposta=proposta,
        event_type="abertura_link",
        prv_id=versao.prvId,
        dados={"origem": "publicacao"},
    )
    db.commit()
    db.refresh(proposta)
    return PropostaResponse.model_validate(proposta)


def list_versoes(db: Session, prp_id: int, company_id: Optional[int], page: int, page_size: int) -> PropostaVersaoListResponse:
    proposta = _get_proposta(db, prp_id, company_id)
    stmt = select(PropostaVersao).where(PropostaVersao.prvPrpId == proposta.prpId).order_by(PropostaVersao.prvNumero.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return PropostaVersaoListResponse(
        items=[PropostaVersaoResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_versao(db: Session, prp_id: int, data: PropostaVersaoCreate, company_id: Optional[int], usu_id: int) -> PropostaVersaoResponse:
    proposta = _get_proposta(db, prp_id, company_id)
    last = db.scalars(
        select(PropostaVersao).where(PropostaVersao.prvPrpId == proposta.prpId).order_by(PropostaVersao.prvNumero.desc()).limit(1)
    ).first()
    num = (last.prvNumero + 1) if last else 1
    versao = PropostaVersao(
        prvEmpId=proposta.prpEmpId,
        prvPrpId=proposta.prpId,
        prvNumero=num,
        prvTitulo=data.prvTitulo or proposta.prpTitulo,
        prvJsonSnapshot=data.prvJsonSnapshot if data.prvJsonSnapshot is not None else proposta.prpJsonConfiguracao,
        prvHtmlSnapshot=data.prvHtmlSnapshot if data.prvHtmlSnapshot is not None else proposta.prpHtmlRenderizado,
        prvPublicada=data.prvPublicada,
        prvUsuId=usu_id,
        prvDataPublicacao=_utcnow() if data.prvPublicada else None,
    )
    db.add(versao)
    db.commit()
    db.refresh(versao)
    return PropostaVersaoResponse.model_validate(versao)


def get_versao(db: Session, prv_id: int, company_id: Optional[int]) -> PropostaVersaoResponse:
    stmt = select(PropostaVersao).where(PropostaVersao.prvId == prv_id)
    if company_id is not None:
        stmt = stmt.where(PropostaVersao.prvEmpId == company_id)
    versao = db.scalars(stmt).first()
    if versao is None:
        raise NotFoundError("Versão da proposta não encontrada")
    return PropostaVersaoResponse.model_validate(versao)


def list_templates(db: Session, company_id: Optional[int], page: int, page_size: int, tipo_proposta: str | None = None) -> PropostaTemplateListResponse:
    stmt = select(PropostaTemplate)
    if company_id is not None:
        stmt = stmt.where(PropostaTemplate.ptlEmpId == company_id)
    if tipo_proposta:
        stmt = stmt.where(PropostaTemplate.ptlTipoProposta == tipo_proposta)
    stmt = stmt.order_by(PropostaTemplate.ptlPadrao.desc(), PropostaTemplate.ptlNome.asc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return PropostaTemplateListResponse(
        items=[PropostaTemplateResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_template(db: Session, ptl_id: int, company_id: Optional[int]) -> PropostaTemplateResponse:
    return PropostaTemplateResponse.model_validate(_get_template(db, ptl_id, company_id))


def create_template(db: Session, data: PropostaTemplateCreate, company_id: Optional[int]) -> PropostaTemplateResponse:
    if company_id is None:
        raise BadRequestError("Empresa atual é obrigatória para criar template")
    template = PropostaTemplate(ptlEmpId=company_id, **data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return PropostaTemplateResponse.model_validate(template)


def update_template(db: Session, ptl_id: int, data: PropostaTemplateUpdate, company_id: Optional[int]) -> PropostaTemplateResponse:
    template = _get_template(db, ptl_id, company_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(template, k, v)
    db.add(template)
    db.commit()
    db.refresh(template)
    return PropostaTemplateResponse.model_validate(template)


def set_template_ativo(db: Session, ptl_id: int, ativo: bool, company_id: Optional[int]) -> PropostaTemplateResponse:
    template = _get_template(db, ptl_id, company_id)
    template.ptlAtivo = ativo
    db.add(template)
    db.commit()
    db.refresh(template)
    return PropostaTemplateResponse.model_validate(template)


def list_blocos(db: Session, prp_id: int, company_id: Optional[int], page: int, page_size: int) -> PropostaBlocoListResponse:
    proposta = _get_proposta(db, prp_id, company_id)
    stmt = select(PropostaBloco).where(PropostaBloco.pblPrpId == proposta.prpId).order_by(PropostaBloco.pblOrdem.asc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return PropostaBlocoListResponse(
        items=[PropostaBlocoResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_bloco(db: Session, prp_id: int, data: PropostaBlocoCreate, company_id: Optional[int]) -> PropostaBlocoResponse:
    proposta = _get_proposta(db, prp_id, company_id)
    bloco = PropostaBloco(
        pblEmpId=proposta.prpEmpId,
        pblPrpId=proposta.prpId,
        **data.model_dump(),
    )
    db.add(bloco)
    db.commit()
    db.refresh(bloco)
    return PropostaBlocoResponse.model_validate(bloco)


def update_bloco(db: Session, pbl_id: int, data: PropostaBlocoUpdate, company_id: Optional[int]) -> PropostaBlocoResponse:
    stmt = select(PropostaBloco).where(PropostaBloco.pblId == pbl_id)
    if company_id is not None:
        stmt = stmt.where(PropostaBloco.pblEmpId == company_id)
    bloco = db.scalars(stmt).first()
    if bloco is None:
        raise NotFoundError("Bloco da proposta não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(bloco, k, v)
    db.add(bloco)
    db.commit()
    db.refresh(bloco)
    return PropostaBlocoResponse.model_validate(bloco)


def reordenar_bloco(db: Session, pbl_id: int, nova_ordem: int, company_id: Optional[int]) -> PropostaBlocoResponse:
    return update_bloco(db, pbl_id, PropostaBlocoUpdate(pblOrdem=nova_ordem), company_id)


def set_visibilidade_bloco(db: Session, pbl_id: int, visivel: bool, company_id: Optional[int]) -> PropostaBlocoResponse:
    return update_bloco(db, pbl_id, PropostaBlocoUpdate(pblVisivel=visivel), company_id)


def list_eventos(db: Session, prp_id: int, company_id: Optional[int], page: int, page_size: int) -> PropostaEventoListResponse:
    proposta = _get_proposta(db, prp_id, company_id)
    stmt = select(PropostaEvento).where(PropostaEvento.pevPrpId == proposta.prpId).order_by(PropostaEvento.pevDataEvento.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return PropostaEventoListResponse(
        items=[PropostaEventoResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_blocos_padroes(
    db: Session,
    company_id: Optional[int],
    page: int,
    page_size: int,
    ptl_id: int | None = None,
    tipo: str | None = None,
) -> PropostaBlocoPadraoListResponse:
    stmt = select(PropostaBlocoPadrao)
    if company_id is not None:
        stmt = stmt.where(PropostaBlocoPadrao.pbpEmpId == company_id)
    if ptl_id is not None:
        stmt = stmt.where(PropostaBlocoPadrao.pbpPtlId == ptl_id)
    if tipo:
        stmt = stmt.where(PropostaBlocoPadrao.pbpTipo == tipo)
    stmt = stmt.order_by(PropostaBlocoPadrao.pbpOrdem.asc(), PropostaBlocoPadrao.pbpId.asc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return PropostaBlocoPadraoListResponse(
        items=[PropostaBlocoPadraoResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_bloco_padrao(db: Session, data: PropostaBlocoPadraoCreate, company_id: Optional[int]) -> PropostaBlocoPadraoResponse:
    if company_id is None:
        raise BadRequestError("Empresa atual é obrigatória para criar bloco padrão")
    if data.pbpPtlId is not None:
        _get_template(db, data.pbpPtlId, company_id)
    obj = PropostaBlocoPadrao(pbpEmpId=company_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return PropostaBlocoPadraoResponse.model_validate(obj)


def update_bloco_padrao(
    db: Session,
    pbp_id: int,
    data: PropostaBlocoPadraoUpdate,
    company_id: Optional[int],
) -> PropostaBlocoPadraoResponse:
    stmt = select(PropostaBlocoPadrao).where(PropostaBlocoPadrao.pbpId == pbp_id)
    if company_id is not None:
        stmt = stmt.where(PropostaBlocoPadrao.pbpEmpId == company_id)
    obj = db.scalars(stmt).first()
    if obj is None:
        raise NotFoundError("Bloco padrão não encontrado")
    payload = data.model_dump(exclude_unset=True)
    if "pbpPtlId" in payload and payload["pbpPtlId"] is not None:
        _get_template(db, int(payload["pbpPtlId"]), company_id)
    for k, v in payload.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return PropostaBlocoPadraoResponse.model_validate(obj)


def set_bloco_padrao_ativo(
    db: Session,
    pbp_id: int,
    ativo: bool,
    company_id: Optional[int],
) -> PropostaBlocoPadraoResponse:
    return update_bloco_padrao(db, pbp_id, PropostaBlocoPadraoUpdate(pbpAtivo=ativo), company_id)


def get_proposta_publica_por_token(db: Session, token: str) -> tuple[Proposta, PropostaPublicaResumoResponse]:
    proposta = db.scalars(select(Proposta).where(Proposta.prpTokenPublico == token, Proposta.prpAtivo.is_(True))).first()
    if proposta is None:
        raise NotFoundError("Proposta pública não encontrada")
    resumo = PropostaPublicaResumoResponse(
        prpId=proposta.prpId,
        prpTitulo=proposta.prpTitulo,
        prpTipo=proposta.prpTipo,  # type: ignore[arg-type]
        prpStatus=proposta.prpStatus,
        prpPublicadaEm=proposta.prpPublicadaEm,
        prpAceitaEm=proposta.prpAceitaEm,
        prpWhatsappContato=proposta.prpWhatsappContato,
        prpHtmlRenderizado=proposta.prpHtmlRenderizado,
        prpJsonConfiguracao=proposta.prpJsonConfiguracao,
    )
    return proposta, resumo


def registrar_evento_publico(
    db: Session,
    token: str,
    event_type: str,
    ip: str | None = None,
    user_agent: str | None = None,
    dados: dict | None = None,
) -> PropostaEventoResponse:
    proposta, _ = get_proposta_publica_por_token(db, token)
    versao = db.scalars(
        select(PropostaVersao)
        .where(PropostaVersao.prvPrpId == proposta.prpId, PropostaVersao.prvNumero == proposta.prpVersaoAtual)
        .limit(1)
    ).first()
    event = _create_event(
        db=db,
        proposta=proposta,
        event_type=event_type,
        prv_id=versao.prvId if versao else None,
        ip=ip,
        user_agent=user_agent,
        dados=dados,
    )
    if event_type == "visualizacao" and proposta.prpStatus in {"publicada", "enviada", "rascunho"}:
        proposta.prpStatus = "visualizada"
        db.add(proposta)
    if event_type == "aceite":
        proposta.prpStatus = "aceita"
        proposta.prpAceitaEm = _utcnow()
        db.add(proposta)
    db.commit()
    db.refresh(event)
    return PropostaEventoResponse.model_validate(event)


def get_public_html(db: Session, token: str, preview: bool = False) -> str:
    proposta, _ = get_proposta_publica_por_token(db, token)
    whatsapp_number = _normalize_whatsapp_number(_get_responsavel_whatsapp(db, proposta))
    if preview:
        empresa = db.get(Empresa, proposta.prpEmpId)
        logo_url = empresa.empLogoUrl if empresa else None  # type: ignore[attr-defined]
        return _render_public_html(proposta, whatsapp_number, logo_url)
    if proposta.prpHtmlRenderizado:
        return proposta.prpHtmlRenderizado
    empresa = db.get(Empresa, proposta.prpEmpId)
    logo_url = empresa.empLogoUrl if empresa else None  # type: ignore[attr-defined]
    html = _render_public_html(proposta, whatsapp_number, logo_url)
    proposta.prpHtmlRenderizado = html
    db.add(proposta)
    db.commit()
    return html


def build_whatsapp_link(db: Session, token: str) -> str:
    proposta, _ = get_proposta_publica_por_token(db, token)
    number = _normalize_whatsapp_number(_get_responsavel_whatsapp(db, proposta))
    if number is None:
        return "#"
    message = quote_plus(f"Olá! Tenho interesse na proposta '{proposta.prpTitulo}'.")
    return f"https://wa.me/{number}?text={message}"

