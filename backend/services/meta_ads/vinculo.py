"""
Liga oportunidades as campanhas do Meta pelo texto que chega nos campos UTM.

Regra: normaliza (minusculas, espacos colapsados) cada campo candidato e procura, na
empresa do lead, campanha com aquele id externo ou aquele nome normalizado. Liga so se
exatamente UMA campanha casar. Nunca mexe em oportunidade ja ligada ou marcada como manual.
Nenhuma funcao daqui faz commit: quem chama decide a transacao.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ...models.meta_ads_campanha import MetaAdsCampanha
from ...models.oportunidade import Oportunidade

CAMPOS_CANDIDATOS = (
    "opoUtmCampaign",
    "opoUtmSource",
    "opoUtmContent",
    "opoUtmTerm",
    "opoOrigemExternalId",
)


def normalizar_nome(texto: str | None) -> str:
    return " ".join((texto or "").split()).lower()


def candidatos(opo) -> set[str]:
    textos = (normalizar_nome(getattr(opo, campo, None)) for campo in CAMPOS_CANDIDATOS)
    return {t for t in textos if t}


class IndiceCampanhas:
    """Campanhas de uma empresa indexadas por id externo e por nome normalizado."""

    def __init__(self, linhas) -> None:
        self._por_texto: dict[str, set[int]] = {}
        for mcg_id, externa, nome_normalizado in linhas:
            for chave in (externa, nome_normalizado):
                if chave:
                    self._por_texto.setdefault(chave, set()).add(mcg_id)

    @classmethod
    def da_empresa(cls, db: Session, emp_id: int) -> "IndiceCampanhas":
        linhas = db.execute(
            select(
                MetaAdsCampanha.mcgId,
                MetaAdsCampanha.mcgCampanhaExterna,
                MetaAdsCampanha.mcgNomeNormalizado,
            ).where(MetaAdsCampanha.mcgEmpId == emp_id)
        ).all()
        return cls(linhas)

    def resolver(self, textos: set[str]) -> int | None:
        achados: set[int] = set()
        for texto in textos:
            achados |= self._por_texto.get(texto, set())
        return next(iter(achados)) if len(achados) == 1 else None


def vincular_oportunidade(
    db: Session, opo: Oportunidade, indice: IndiceCampanhas | None = None
) -> bool:
    if opo.opoMcgManual or opo.opoMcgId is not None:
        return False
    textos = candidatos(opo)
    if not textos:
        return False
    indice = indice or IndiceCampanhas.da_empresa(db, opo.opoEmpId)
    mcg_id = indice.resolver(textos)
    if mcg_id is None:
        return False
    opo.opoMcgId = mcg_id
    return True


def vincular_pendentes(db: Session, emp_id: int) -> int:
    indice = IndiceCampanhas.da_empresa(db, emp_id)
    tem_candidato = or_(*[getattr(Oportunidade, c).isnot(None) for c in CAMPOS_CANDIDATOS])
    pendentes = db.execute(
        select(Oportunidade).where(
            Oportunidade.opoEmpId == emp_id,
            Oportunidade.opoMcgId.is_(None),
            Oportunidade.opoMcgManual.is_(False),
            tem_candidato,
        )
    ).scalars()
    return sum(1 for opo in pendentes if vincular_oportunidade(db, opo, indice))
