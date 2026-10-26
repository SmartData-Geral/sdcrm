"""Registro estruturado de transicoes de estagio e carga retroativa a partir do texto livre."""

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.etapa_kanban import EtapaKanban
from ..models.oportunidade import Oportunidade
from ..models.oportunidade_etapa_historico import OportunidadeEtapaHistorico as Oeh
from ..models.oportunidade_historico import OportunidadeHistorico

REGEX_TRANSICAO = re.compile(r'Etapa alterada de "(.*?)" para "(.*?)"\.')


def registrar_transicao(
    db: Session,
    opo: Oportunidade,
    etk_de: int | None,
    etk_para: int | None,
    origem: str,
    quando: datetime | None = None,
) -> None:
    """Grava a transicao na transacao do chamador (sem commit). Ignora de == para."""
    if etk_de == etk_para:
        return
    db.add(
        Oeh(
            oehEmpId=opo.opoEmpId,
            oehOpoId=opo.opoId,
            oehEtkIdDe=etk_de,
            oehEtkIdPara=etk_para,
            oehData=quando or datetime.now(timezone.utc),
            oehOrigem=origem,
        )
    )


def _norm(nome: str) -> str:
    return " ".join((nome or "").split()).lower()


def _chave_data(d: datetime) -> datetime:
    return d.replace(tzinfo=None) if d.tzinfo else d


def carga_retroativa(db: Session, emp_id: int, *, aplicar: bool) -> dict:
    etapas = db.scalars(select(EtapaKanban).where(EtapaKanban.etkEmpId == emp_id)).all()
    por_nome: dict[str, list[EtapaKanban]] = {}
    for e in etapas:
        por_nome.setdefault(_norm(e.etkNome), []).append(e)
    pipeline_de = {e.etkId: e.etkPipeline for e in etapas}

    def resolver(nome: str, pipeline: str | None) -> int | None:
        candidatas = por_nome.get(_norm(nome), [])
        if not candidatas:
            return None
        if len(candidatas) > 1 and pipeline is not None:
            do_pipeline = [e for e in candidatas if e.etkPipeline == pipeline]
            if do_pipeline:
                return do_pipeline[0].etkId
        return candidatas[0].etkId

    contagem = {"transicoes": 0, "criacoes": 0, "nao_casadas": 0}
    oportunidades = db.scalars(select(Oportunidade).where(Oportunidade.opoEmpId == emp_id)).all()
    for opo in oportunidades:
        existentes = db.scalars(select(Oeh).where(Oeh.oehOpoId == opo.opoId)).all()
        if any(x.oehOrigem == "retroativo" for x in existentes):
            continue
        chaves = {(x.oehEtkIdPara, _chave_data(x.oehData)) for x in existentes}
        tem_criacao = any(x.oehEtkIdDe is None for x in existentes)
        pipeline = pipeline_de.get(opo.opoEtkId)

        linhas = db.scalars(
            select(OportunidadeHistorico)
            .where(OportunidadeHistorico.ophOpoId == opo.opoId)
            .order_by(OportunidadeHistorico.ophDataRegistro, OportunidadeHistorico.ophId)
        ).all()
        encontradas = []
        for h in linhas:
            m = REGEX_TRANSICAO.search(h.ophConteudo or "")
            if m:
                encontradas.append((h.ophDataRegistro, m.group(1), m.group(2)))

        novas = []
        estagio_inicial = None
        for i, (data, nome_de, nome_para) in enumerate(encontradas):
            de = resolver(nome_de, pipeline)
            para = resolver(nome_para, pipeline)
            if i == 0:
                estagio_inicial = de
            if de is None or para is None:
                contagem["nao_casadas"] += 1
                continue
            if (para, _chave_data(data)) in chaves:
                continue
            novas.append((de, para, data))
        if not encontradas:
            estagio_inicial = opo.opoEtkId

        for de, para, data in novas:
            contagem["transicoes"] += 1
            if aplicar:
                db.add(
                    Oeh(
                        oehEmpId=emp_id, oehOpoId=opo.opoId, oehEtkIdDe=de,
                        oehEtkIdPara=para, oehData=data, oehOrigem="retroativo",
                    )
                )
        if estagio_inicial is not None and not tem_criacao:
            contagem["criacoes"] += 1
            if aplicar:
                db.add(
                    Oeh(
                        oehEmpId=emp_id, oehOpoId=opo.opoId, oehEtkIdDe=None,
                        oehEtkIdPara=estagio_inicial, oehData=opo.opoDataCriacao,
                        oehOrigem="retroativo",
                    )
                )
    if aplicar:
        db.commit()
    return contagem
