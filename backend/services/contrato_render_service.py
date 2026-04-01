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
from sqlalchemy.orm import Session

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
        "forma_pagamento": contrato.ctrFormaPagamento,
        "vigencia": contrato.ctrVigencia,
        "data_inicio": _format_data_brl_iso(contrato.ctrDataInicio),
        "foro": contrato.ctrForo,
        "reajuste": contrato.ctrReajuste or "",
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
            items = []
            for line in lines:
                m = _LIST_BULLET_ORDERED_RE.match(line)
                if not m:
                    continue
                content = line[m.end() :].strip()
                items.append(f"<li>{content}</li>")
            parts.append(f"<ol>{''.join(items)}</ol>")
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
            parts.append(f"<p>{p.replace('\n', '<br/>')}</p>")
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


def _contract_html_header(contrato: Contrato) -> str:
    return f"""
<div class="contract-header">
  <div class="contract-brand">
    <div class="brand-dot"></div>
    <div>
      <div class="brand-title">Contrato</div>
      <div class="brand-subtitle">Documento gerado a partir do modelo Smart Data</div>
    </div>
  </div>

  <div class="contract-meta">
    <div><span class="meta-label">Objeto</span><span class="meta-value">{html.escape(contrato.ctrObjetoContrato)}</span></div>
    <div><span class="meta-label">Valor</span><span class="meta-value">{html.escape(_format_valor_brl(contrato.ctrValorContrato))}</span></div>
    <div><span class="meta-label">Forma de pagamento</span><span class="meta-value">{html.escape(contrato.ctrFormaPagamento)}</span></div>
    <div><span class="meta-label">Vigência</span><span class="meta-value">{html.escape(contrato.ctrVigencia)}</span></div>
    <div><span class="meta-label">Início</span><span class="meta-value">{html.escape(_format_data_brl_iso(contrato.ctrDataInicio))}</span></div>
    <div><span class="meta-label">Foro</span><span class="meta-value">{html.escape(contrato.ctrForo)}</span></div>
    <div><span class="meta-label">Reajuste</span><span class="meta-value">{html.escape(contrato.ctrReajuste or "-")}</span></div>
  </div>
</div>
"""


def gerar_html_contrato(db: Session, contrato_id: int) -> str:
    contrato = db.scalars(select(Contrato).where(Contrato.ctrId == contrato_id, Contrato.ctrAtivo.is_(True))).first()
    if contrato is None:
        raise NotFoundError("Contrato não encontrado")

    used_clauses = _recalcular_ordem_final(db, contrato_id)
    values = _placeholder_values(contrato)

    style = """
<style>
  body { font-family: "Plus Jakarta Sans", "Inter", system-ui, -apple-system, Segoe UI, Arial, sans-serif; margin: 0; background: #f8fafc; color: #0f172a; }
  .wrap { max-width: 980px; margin: 0 auto; padding: 32px 18px 40px; }
  .contract-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 16px; box-shadow: 0 10px 32px rgba(15,23,42,0.06); overflow: hidden; }
  .contract-header { padding: 26px 24px; background: linear-gradient(140deg, #0f172a 0%, #1d4ed8 55%, #2563eb 100%); color: #fff; }
  .contract-brand { display: flex; gap: 12px; align-items: center; margin-bottom: 18px; }
  .brand-dot { width: 12px; height: 12px; border-radius: 999px; background: #93c5fd; box-shadow: 0 0 0 6px rgba(147,197,253,0.18); }
  .brand-title { font-size: 20px; font-weight: 800; letter-spacing: -0.01em; }
  .brand-subtitle { font-size: 12px; opacity: .9; margin-top: 4px; }
  .contract-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 18px; }
  .meta-label { display: block; font-size: 11px; opacity: .78; margin-bottom: 3px; }
  .meta-value { display: block; font-size: 13px; font-weight: 650; }
  .contract-body { padding: 26px 24px 14px; }
  .section-title { font-size: 15px; letter-spacing: .08em; text-transform: uppercase; font-weight: 800; color: #1d4ed8; margin: 0 0 10px; }
  .parties-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 18px; }
  .party-card { border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px; }
  .party-label { font-size: 11px; opacity: .7; margin-bottom: 6px; }
  .party-value { font-size: 13px; font-weight: 650; white-space: pre-wrap; }
  .clause { margin-top: 18px; padding-top: 14px; border-top: 1px solid #e5e7eb; }
  .clause h3 { margin: 0 0 8px; font-size: 14px; font-weight: 850; color: #0f172a; }
  .clause-body p { margin: 0 0 10px; line-height: 1.65; }
  .clause-body ul, .clause-body ol { margin: 0 0 12px 18px; }
  .contract-footer { padding: 18px 24px 26px; color: #64748b; font-size: 12px; }
  .contract-footer hr { border: none; border-top: 1px solid #e5e7eb; margin: 0 0 12px; }
</style>
"""

    parties_html = f"""
<div class="parties-grid">
  <div class="party-card">
    <div class="party-label">Contratante</div>
    <div class="party-value">{html.escape(contrato.ctrRazaoSocial)}</div>
    <div class="party-label" style="margin-top:10px;">CNPJ</div>
    <div class="party-value">{html.escape(contrato.ctrCnpj)}</div>
    <div class="party-label" style="margin-top:10px;">Endereço</div>
    <div class="party-value">{html.escape(contrato.ctrEndereco)}</div>
  </div>
  <div class="party-card">
    <div class="party-label">Responsável</div>
    <div class="party-value">{html.escape(contrato.ctrResponsavelNome)}</div>
    <div class="party-label" style="margin-top:10px;">CPF</div>
    <div class="party-value">{html.escape(contrato.ctrResponsavelCpf)}</div>
  </div>
</div>
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
  <h3>{ccl.cclOrdemFinal}. {titulo_rendered}</h3>
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

    html_out = f"<!doctype html><html><head><meta charset='utf-8'>{style}</head><body><div class='wrap'><div class='contract-card'>"
    html_out += _contract_html_header(contrato)
    html_out += "<div class='contract-body'>"
    html_out += "<h2 class='section-title'>Partes</h2>"
    html_out += parties_html
    html_out += "<h2 class='section-title'>Cláusulas</h2>"
    html_out += "".join(clauses_html_parts)
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
        elements.append(Paragraph(f"{ccl.cclOrdemFinal}. {titulo_rendered}", styles["Heading3"]))

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

