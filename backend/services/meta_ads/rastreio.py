"""
Ids da Meta que acompanham o lead (Lead Ads) e o sinal de que o lead veio da Meta.

Regra do primeiro anuncio: o credito fica com o primeiro anuncio que trouxe o lead;
um novo envio por outro anuncio so deixa uma nota no historico.
Nenhuma funcao daqui faz commit: quem chama decide a transacao.
"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...core.tempo import utcnow
from ...models.oportunidade import Oportunidade
from ...models.oportunidade_historico import OportunidadeHistorico

PREFIXOS = ("as:", "ag:", "l:", "c:", "p:")

# Expressao SQL: o lead carrega algum sinal de origem na Meta.
tem_sinal_meta = or_(
    Oportunidade.opoMetaLeadId.isnot(None),
    Oportunidade.opoMetaAnuncioId.isnot(None),
    Oportunidade.opoMcgId.isnot(None),
)


def limpar_id_meta(valor: str | None) -> str | None:
    """Tira espacos e o prefixo de tipo (l:, c:, as:, ag:, p:); vazio vira None."""
    texto = (valor or "").strip()
    for prefixo in PREFIXOS:
        if texto.lower().startswith(prefixo):
            texto = texto[len(prefixo):].strip()
            break
    return texto[:40] or None


def aplicar_ids_meta(
    db: Session,
    opo: Oportunidade,
    *,
    meta_lead_id: str | None,
    campaign_id: str | None,
    adset_id: str | None,
    ad_id: str | None,
) -> bool:
    """Grava os ids so onde estao vazios. False quando outro anuncio ja tinha o credito."""
    novos = {
        "opoMetaLeadId": limpar_id_meta(meta_lead_id),
        "opoMetaCampanhaId": limpar_id_meta(campaign_id),
        "opoMetaConjuntoId": limpar_id_meta(adset_id),
        "opoMetaAnuncioId": limpar_id_meta(ad_id),
    }
    anuncio_atual = opo.opoMetaAnuncioId
    anuncio_novo = novos["opoMetaAnuncioId"]
    if anuncio_atual and anuncio_novo and anuncio_atual != anuncio_novo:
        db.add(
            OportunidadeHistorico(
                ophEmpId=opo.opoEmpId,
                ophOpoId=opo.opoId,
                ophUsuId=None,
                ophDataRegistro=utcnow(),
                ophConteudo="Novo envio pelo anúncio "
                + anuncio_novo
                + " (crédito mantido no primeiro anúncio).",
            )
        )
        return False
    for campo, valor in novos.items():
        if valor is not None and not getattr(opo, campo):
            setattr(opo, campo, valor)
    return True
