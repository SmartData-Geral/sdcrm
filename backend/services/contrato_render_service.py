from __future__ import annotations

import html
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..exceptions import BadRequestError, NotFoundError
from ..models.contrato import Contrato
from ..models.contrato_clausula import ContratoClausula
from ..services.contrato_placeholders import render_placeholders


_TOKEN_PUBLICO_RE = re.compile(r"[^a-zA-Z0-9_-]+")
_PARA_SPLIT_RE = re.compile(r"\n\s*\n+")
_LIST_BULLET_UNORDERED_RE = re.compile(r"^\s*([-•])\s+")
_LIST_BULLET_ORDERED_RE = re.compile(r"^\s*(\d+)[\.\)]\s+")


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _safe_trim(text: str) -> str:
    return (text or "").strip()


def _format_valor_brl(value: Any) -> str:
    if value is None:
        return ""
    try:
        d = Decimal(str(value))
        return f"{d:.2f}".replace(".", ",")
    except Exception:
        return str(value)


def _format_data_brl_iso(date_value: Any) -> str:
    # Espera date/datetime do banco.
    if not date_value:
        return ""
    try:
        return date_value.strftime("%d/%m/%Y")  # type: ignore[union-attr]
    except Exception:
        return str(date_value)


def _placeholder_values(contrato: Contrato) -> dict[str, Any]:
    return {
        "razao_social": contrato.ctrRazaoSocial,
        "cnpj": contrato.ctrCnpj,
        "endereco": contrato.ctrEndereco,
        "responsavel_nome": contrato.ctrResponsavelNome,
        "responsavel_cpf": contrato.ctrResponsavelCpf,
        "objeto_contrato": contrato.ctrObjetoContrato,
        "valor_contrato": _format_valor_brl(contrato.ctrValorContrato),
        "valor_manutencao": _format_valor_brl(contrato.ctrValorManutencao),
        "data_inicio": _format_data_brl_iso(contrato.ctrDataInicio),
        "prazo_conclusao": contrato.ctrPrazoConclusao,
        "dias_pagamento": str(contrato.ctrDiasPagamento),
        "dias_antecedencia_rescisao": str(contrato.ctrDiasAntecedenciaRescisao),
        "horas_melhorias_mensais": str(contrato.ctrHorasMelhoriasMensais),
    }


def _recalcular_ordem_final(db: Session, contrato_id: int) -> list[ContratoClausula]:
    clausulas = db.scalars(
        select(ContratoClausula)
        .where(ContratoClausula.cclCtrId == contrato_id, ContratoClausula.cclAtivo.is_(True))
        .order_by(ContratoClausula.cclOrdemBase.asc(), ContratoClausula.cclId.asc())
    ).all()

    ordem = 1
    used: list[ContratoClausula] = []
    for ccl in clausulas:
        if ccl.cclAtivo and ccl.cclUtilizar:
            ccl.cclOrdemFinal = ordem
            used.append(ccl)
            ordem += 1
        else:
            ccl.cclOrdemFinal = 0

    db.add_all(clausulas)
    db.commit()
    db.flush()
    return used


def _is_list_ordered(lines: list[str]) -> bool:
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return False
    return all(_LIST_BULLET_ORDERED_RE.match(l) is not None for l in non_empty)


def _is_list_unordered(lines: list[str]) -> bool:
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return False
    return all(_LIST_BULLET_UNORDERED_RE.match(l) is not None for l in non_empty)


def _render_text_to_html_paragraphs(rendered_text_escaped: str) -> str:
    """
    rendered_text_escaped já deve estar com placeholders substituídos e com escape de HTML.
    """
    text = _normalize_newlines(rendered_text_escaped)
    if not text.strip():
        return "<p></p>"

    paragraphs = _PARA_SPLIT_RE.split(text)
    parts: list[str] = []
    for p in paragraphs:
        p = p.strip("\n").strip()
        if not p:
            continue
        lines = p.split("\n")
        if _is_list_ordered(lines):
            # Cada parágrafo (bloco entre \n\n) vira um <ol> separado. Com um único <li>, o
            # navegador sempre mostra "1." — usamos start= com o número do texto para manter
            # a numeração original quando o modelo quebra itens em parágrafos distintos.
            non_empty = [ln for ln in lines if ln.strip()]
            first_m = _LIST_BULLET_ORDERED_RE.match(non_empty[0]) if non_empty else None
            start_num = int(first_m.group(1)) if first_m else 1
            items = []
            for line in lines:
                m = _LIST_BULLET_ORDERED_RE.match(line)
                if not m:
                    continue
                content = line[m.end() :].strip()
                items.append(f"<li>{content}</li>")
            start_attr = f' start="{start_num}"' if start_num != 1 else ""
            parts.append(f"<ol{start_attr}>{''.join(items)}</ol>")
        elif _is_list_unordered(lines):
            items = []
            for line in lines:
                m = _LIST_BULLET_UNORDERED_RE.match(line)
                if not m:
                    continue
                content = line[m.end() :].strip()
                items.append(f"<li>{content}</li>")
            parts.append(f"<ul>{''.join(items)}</ul>")
        else:
            paragraph_html = p.replace("\n", "<br/>")
            parts.append(f"<p>{paragraph_html}</p>")
    return "".join(parts)


def _render_text_to_pdf_paragraphs(rendered_text_escaped: str) -> list[str]:
    text = _normalize_newlines(rendered_text_escaped)
    if not text.strip():
        return [""]

    paragraphs = _PARA_SPLIT_RE.split(text)
    lines_out: list[str] = []
    for p in paragraphs:
        p = p.strip("\n").strip()
        if not p:
            continue
        lines = p.split("\n")
        if _is_list_ordered(lines):
            for line in lines:
                m = _LIST_BULLET_ORDERED_RE.match(line)
                if not m:
                    continue
                num = m.group(1)
                content = line[m.end() :].strip()
                lines_out.append(f"{num}. {content}")
        elif _is_list_unordered(lines):
            for line in lines:
                m = _LIST_BULLET_UNORDERED_RE.match(line)
                if not m:
                    continue
                content = line[m.end() :].strip()
                lines_out.append(f"• {content}")
        else:
            # mantém linhas como quebras.
            lines_out.append(p.replace("\n", "<br/>"))
    return lines_out


def gerar_html_contrato(db: Session, contrato_id: int) -> str:
    contrato = db.scalars(
        select(Contrato)
        .where(Contrato.ctrId == contrato_id, Contrato.ctrAtivo.is_(True))
        .options(selectinload(Contrato.empresa))
    ).first()
    if contrato is None:
        raise NotFoundError("Contrato não encontrado")

    empresa_nome = (
        html.escape(contrato.empresa.empNome.strip())
        if contrato.empresa and contrato.empresa.empNome
        else "—"
    )

    used_clauses = _recalcular_ordem_final(db, contrato_id)
    values = _placeholder_values(contrato)

    style = """
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&display=swap" rel="stylesheet"/>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: "Plus Jakarta Sans", "Inter", system-ui, -apple-system, Segoe UI, Arial, sans-serif;
    margin: 0;
    background: #f1f5f9;
    color: #0f172a;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 800px; margin: 0 auto; padding: 24px 16px 40px; }
  .contract-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    box-shadow: 0 4px 24px -8px rgba(15, 23, 42, 0.1);
    overflow: hidden;
  }
  .contract-body { padding: 0 0 8px; }

  .clauses-doc-header {
    margin: 0;
    padding: 28px 32px 24px;
    background: linear-gradient(180deg, #f8fafc 0%, #fff 55%);
    border-bottom: 1px solid #e8edf3;
  }
  .clauses-doc-kicker {
    margin: 0 0 6px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #64748b;
  }
  .clauses-doc-title {
    margin: 0;
    font-size: clamp(1.5rem, 4vw, 1.875rem);
    font-weight: 800;
    letter-spacing: -0.035em;
    line-height: 1.15;
    color: #0f172a;
  }
  .clauses-doc-title-accent {
    display: block;
    width: 3rem;
    height: 4px;
    margin-top: 14px;
    border-radius: 999px;
    background: linear-gradient(90deg, #1e40af, #3b82f6, #93c5fd);
  }

  .clauses-stack { padding: 8px 32px 0; }

  .clause {
    margin-top: 24px;
    padding-top: 22px;
    border-top: 1px solid #eef2f7;
  }
  .clause:first-of-type { margin-top: 0; padding-top: 20px; border-top: none; }
  .clause h3.clause-title {
    margin: 0 0 14px;
    display: flex;
    align-items: center;
    font-size: 15px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.02em;
    line-height: 1.3;
  }
  .clause-title-accent {
    display: block;
    width: 4px;
    min-height: 1.35em;
    margin-right: 12px;
    flex-shrink: 0;
    border-radius: 4px;
    background: linear-gradient(180deg, #1e40af 0%, #3b82f6 52%, #93c5fd 100%);
  }
  .clause-title-text {
    flex: 1;
    min-width: 0;
  }
  .clause-body p { margin: 0 0 12px; line-height: 1.75; color: #334155; font-size: 14px; }
  .clause-body ul, .clause-body ol { margin: 0 0 14px 20px; color: #334155; font-size: 14px; }

  .contract-footer { padding: 22px 32px 28px; color: #94a3b8; font-size: 12px; line-height: 1.55; }
  .contract-footer hr { border: none; border-top: 1px solid #e8edf3; margin: 0 0 14px; }

  @media (max-width: 520px) {
    .clauses-doc-header, .clauses-stack { padding-left: 20px; padding-right: 20px; }
  }
</style>
"""

    clauses_html_parts: list[str] = []
    for ccl in sorted(used_clauses, key=lambda x: x.cclOrdemFinal or 0):
        values = values  # keep
        titulo_rendered = render_placeholders(ccl.cclTitulo or "", values)
        texto_rendered = render_placeholders(ccl.cclTexto or "", values)
        clause_text_html = _render_text_to_html_paragraphs(texto_rendered)
        clauses_html_parts.append(
            f"""
<section class="clause">
  <h3 class="clause-title">
    <span class="clause-title-accent" aria-hidden="true"></span>
    <span class="clause-title-text">{titulo_rendered}</span>
  </h3>
  <div class="clause-body">{clause_text_html}</div>
</section>
"""
        )

    footer = """
<div class="contract-footer">
  <hr/>
  <div>
    Este contrato foi gerado eletronicamente com base nas cláusulas selecionadas e editadas pelo usuário.
  </div>
</div>
"""

    clauses_heading = f"""
<header class="clauses-doc-header">
  <p class="clauses-doc-kicker">{empresa_nome}</p>
  <h1 class="clauses-doc-title">Contrato Prestação de Serviço</h1>
  <span class="clauses-doc-title-accent" aria-hidden="true"></span>
</header>
"""

    html_out = f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/>{style}</head><body><div class='wrap'><div class='contract-card'><div class='contract-body'>"
    html_out += clauses_heading
    html_out += "<div class='clauses-stack'>"
    html_out += "".join(clauses_html_parts)
    html_out += "</div>"
    html_out += "</div>"
    html_out += footer
    html_out += "</div></div></body></html>"
    return html_out


def gerar_pdf_contrato(
    db: Session,
    contrato_id: int,
    pdf_dir: Path,
    html_snapshot: str | None = None,
) -> str:
    contrato = db.scalars(select(Contrato).where(Contrato.ctrId == contrato_id, Contrato.ctrAtivo.is_(True))).first()
    if contrato is None:
        raise NotFoundError("Contrato não encontrado")

    pdf_dir.mkdir(parents=True, exist_ok=True)

    # Gera HTML para garantir numeração e placeholders consistentes.
    # (Pode ser passado pelo endpoint para evitar recalcular.)
    if html_snapshot is None:
        html_snapshot = gerar_html_contrato(db=db, contrato_id=contrato_id)

    # Monta doc PDF
    safe_token = _TOKEN_PUBLICO_RE.sub("_", (contrato.ctrTokenPublico or str(contrato.ctrId)))
    filename = f"{contrato.ctrId}_{safe_token}.pdf"
    pdf_path = pdf_dir / filename

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    normal = styles["BodyText"]
    normal.spaceAfter = 8  # type: ignore[attr-defined]

    elements: list[Any] = []
    elements.append(Paragraph("Contrato", title_style))
    elements.append(Paragraph(f"Responsável: {html.escape(contrato.ctrResponsavelNome)}", normal))
    elements.append(Spacer(1, 10))

    values = _placeholder_values(contrato)
    used_clauses = db.scalars(
        select(ContratoClausula)
        .where(
            ContratoClausula.cclCtrId == contrato_id,
            ContratoClausula.cclAtivo.is_(True),
            ContratoClausula.cclUtilizar.is_(True),
        )
        .order_by(ContratoClausula.cclOrdemFinal.asc(), ContratoClausula.cclId.asc())
    ).all()

    for ccl in used_clauses:
        titulo_rendered = render_placeholders(ccl.cclTitulo or "", values)
        texto_rendered = render_placeholders(ccl.cclTexto or "", values)
        elements.append(Paragraph(titulo_rendered, styles["Heading3"]))

        # Divide em itens (parágrafos ou linhas de lista)
        parts = _render_text_to_pdf_paragraphs(texto_rendered)
        for idx, part in enumerate(parts):
            if idx > 0 and part and not part.startswith("<br"):
                elements.append(Spacer(1, 6))
            elements.append(Paragraph(part if part else " ", normal))

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=48, bottomMargin=48)
    doc.build(elements)
    _ = html_snapshot  # garante que o PDF foi gerado a partir do mesmo estado
    return str(pdf_path)

