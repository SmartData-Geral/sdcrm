"""
Liga oportunidades as campanhas do Meta pelo texto que chega nos campos UTM.

Primeiro, o id do anuncio vindo da Meta (opoMetaAnuncioId) resolve o anuncio e a campanha.
Depois, a regra por texto: normaliza (minusculas, espacos colapsados) cada campo candidato e procura, na
empresa do lead, campanha com aquele id externo ou aquele nome normalizado. Liga so se
exatamente UMA campanha casar. Nunca mexe em oportunidade ja ligada ou marcada como manual.
Nenhuma funcao daqui faz commit: quem chama decide a transacao.
"""

from __future__ import annotations

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from ...models.meta_ads_anuncio import MetaAdsAnuncio
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


def _anuncio_da_empresa(db: Session, emp_id: int, anuncio_externo: str):
    """Anuncio sincronizado com esse id externo; None se nao existe ou se for ambiguo."""
    achados = db.execute(
        select(MetaAdsAnuncio.manId, MetaAdsAnuncio.manMcgId).where(
            MetaAdsAnuncio.manEmpId == emp_id,
            MetaAdsAnuncio.manAnuncioExterno == anuncio_externo,
        )
    ).all()
    return achados[0] if len(achados) == 1 else None


def _vincular_por_anuncio(db: Session, opo: Oportunidade) -> bool:
    if not opo.opoMetaAnuncioId:
        return False
    achado = _anuncio_da_empresa(db, opo.opoEmpId, opo.opoMetaAnuncioId)
    if achado is None:
        return False
    man_id, mcg_id = achado
    mudou = False
    if opo.opoManId is None:
        opo.opoManId = man_id
        mudou = True
    if opo.opoMcgId is None and not opo.opoMcgManual:
        opo.opoMcgId = mcg_id
        mudou = True
    return mudou


def vincular_oportunidade(
    db: Session, opo: Oportunidade, indice: IndiceCampanhas | None = None
) -> bool:
    # Primeiro pelo anuncio (id exato vindo da Meta); so depois a regra por nome/UTM.
    mudou = _vincular_por_anuncio(db, opo)
    if opo.opoMcgManual or opo.opoMcgId is not None:
        return mudou
    textos = candidatos(opo)
    if not textos:
        return mudou
    indice = indice or IndiceCampanhas.da_empresa(db, opo.opoEmpId)
    mcg_id = indice.resolver(textos)
    if mcg_id is None:
        return mudou
    opo.opoMcgId = mcg_id
    return True


def _ligar_se_pendente(db: Session, opo_id: int, mcg_id: int) -> bool:
    """UPDATE guardado: so liga se a oportunidade ainda esta sem campanha e nao e manual.

    No MySQL (REPEATABLE READ) a leitura de `vincular_pendentes` pode vir de um snapshot
    antigo; sem a guarda, uma escolha manual feita nesse intervalo seria sobrescrita.
    O SQLite dos testes nao reproduz essa corrida.
    """
    resultado = db.execute(
        update(Oportunidade)
        .where(
            Oportunidade.opoId == opo_id,
            Oportunidade.opoMcgId.is_(None),
            Oportunidade.opoMcgManual.is_(False),
        )
        .values(opoMcgId=mcg_id)
        .execution_options(synchronize_session=False)
    )
    return resultado.rowcount == 1


def _ligar_anuncio_se_pendente(
    db: Session, opo_id: int, man_id: int, mcg_id: int, ligar_campanha: bool
) -> bool:
    """UPDATEs guardados do vinculo por anuncio (mesma razao de `_ligar_se_pendente`)."""
    mudou = db.execute(
        update(Oportunidade)
        .where(Oportunidade.opoId == opo_id, Oportunidade.opoManId.is_(None))
        .values(opoManId=man_id)
        .execution_options(synchronize_session=False)
    ).rowcount == 1
    if ligar_campanha and _ligar_se_pendente(db, opo_id, mcg_id):
        mudou = True
    return mudou


def vincular_pendentes(db: Session, emp_id: int) -> int:
    indice = IndiceCampanhas.da_empresa(db, emp_id)
    anuncios: dict[str, set[tuple[int, int]]] = {}
    for man_id, mcg_id, externo in db.execute(
        select(
            MetaAdsAnuncio.manId, MetaAdsAnuncio.manMcgId, MetaAdsAnuncio.manAnuncioExterno
        ).where(MetaAdsAnuncio.manEmpId == emp_id)
    ).all():
        anuncios.setdefault(externo, set()).add((man_id, mcg_id))

    tem_candidato = or_(*[getattr(Oportunidade, c).isnot(None) for c in CAMPOS_CANDIDATOS])
    sem_campanha = (Oportunidade.opoMcgId.is_(None)) & (Oportunidade.opoMcgManual.is_(False))
    sem_anuncio = (Oportunidade.opoManId.is_(None)) & (Oportunidade.opoMetaAnuncioId.isnot(None))
    pendentes = db.execute(
        select(Oportunidade).where(
            Oportunidade.opoEmpId == emp_id,
            or_(sem_anuncio, sem_campanha & tem_candidato),
        )
    ).scalars().all()
    total = 0
    for opo in pendentes:
        ligou = False
        achados = anuncios.get(opo.opoMetaAnuncioId or "", set())
        if len(achados) == 1:
            man_id, mcg_id = next(iter(achados))
            ligou = _ligar_anuncio_se_pendente(
                db, opo.opoId, man_id, mcg_id, ligar_campanha=not opo.opoMcgManual
            )
        if not ligou and opo.opoMcgId is None and not opo.opoMcgManual:
            mcg_id = indice.resolver(candidatos(opo))
            ligou = mcg_id is not None and _ligar_se_pendente(db, opo.opoId, mcg_id)
        if ligou:
            total += 1
    return total
