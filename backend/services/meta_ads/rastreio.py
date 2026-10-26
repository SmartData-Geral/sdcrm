"""
Ids da Meta que acompanham o lead (Lead Ads) e o sinal de que o lead veio da Meta.

Regra do primeiro anuncio: o credito fica com o primeiro anuncio que trouxe o lead;
um novo envio por outro anuncio so deixa uma nota no historico.
Nenhuma funcao daqui faz commit: quem chama decide a transacao.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ...core.tempo import utcnow
from ...models.meta_ads_anuncio import MetaAdsAnuncio
from ...models.oportunidade import Oportunidade
from ...models.oportunidade_historico import OportunidadeHistorico
from ...schemas.lead_integracao import RastreioMetaItem, RastreioMetaResponse
from ..lead_normalizacao import normalizar_email, normalizar_telefone, variantes_telefone

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


def _nome_do_anuncio(db: Session, emp_id: int, anuncio_externo: str) -> str:
    """Nome do anuncio sincronizado na empresa; o proprio id se nao achar (ou se for ambiguo)."""
    nomes = db.scalars(
        select(MetaAdsAnuncio.manNome).where(
            MetaAdsAnuncio.manEmpId == emp_id, MetaAdsAnuncio.manAnuncioExterno == anuncio_externo
        )
    ).all()
    return nomes[0] if len(nomes) == 1 and nomes[0] else anuncio_externo


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
                + _nome_do_anuncio(db, opo.opoEmpId, anuncio_novo)
                + " (crédito mantido no primeiro anúncio).",
            )
        )
        return False
    for campo, valor in novos.items():
        if valor is not None and not getattr(opo, campo):
            setattr(opo, campo, valor)
    return True


def _ativas_da_empresa(emp_id: int):
    return select(Oportunidade).where(
        Oportunidade.opoEmpId == emp_id, Oportunidade.opoAtivo.is_(True)
    )


def _casar(db: Session, emp_id: int, item: RastreioMetaItem) -> list[Oportunidade]:
    """Primeiro criterio que achar alguem vence: id do lead, telefone, e-mail."""
    lead_id = limpar_id_meta(item.meta_lead_id)
    criterios = []
    if lead_id:
        criterios.append(
            or_(Oportunidade.opoMetaLeadId == lead_id, Oportunidade.opoOrigemExternalId == lead_id)
        )
    fones = variantes_telefone(normalizar_telefone(item.phone))
    if fones:
        criterios.append(Oportunidade.opoTelefoneNormalizado.in_(sorted(fones)))
    email = normalizar_email(item.email)
    if email:
        criterios.append(Oportunidade.opoEmailNormalizado == email)
    for criterio in criterios:
        achadas = list(db.scalars(_ativas_da_empresa(emp_id).where(criterio)))
        if achadas:
            return achadas
    return []


def aplicar_rastreio_retroativo(
    db: Session, emp_id: int, itens: list[RastreioMetaItem]
) -> RastreioMetaResponse:
    """
    Liga leads ja existentes aos ids da Meta a partir da planilha de formularios.
    Nunca cria lead. Em ordem de created_time, entao o primeiro anuncio vence.
    Um unico commit no fim, depois de vincular as pendentes.

    O chamador deve enviar as linhas da planilha inteira em ordem crescente de created_time
    (lotes em sequência); a regra 'a mais antiga vence' vale entre lotes só nessa condição.
    """
    from . import vinculo

    resp = RastreioMetaResponse()
    for item in sorted(itens, key=lambda i: i.created_time):
        achadas = _casar(db, emp_id, item)
        if not achadas:
            resp.nao_casados += 1
        elif len(achadas) > 1:
            resp.ambiguos += 1
        elif achadas[0].opoMetaAnuncioId:
            resp.ja_atribuidos += 1
        else:
            aplicar_ids_meta(
                db,
                achadas[0],
                meta_lead_id=item.meta_lead_id,
                campaign_id=item.campaign_id,
                adset_id=item.adset_id,
                ad_id=item.ad_id,
            )
            db.flush()
            resp.casados += 1
    vinculo.vincular_pendentes(db, emp_id)
    db.commit()
    return resp
