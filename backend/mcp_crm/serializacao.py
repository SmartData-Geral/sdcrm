"""JSON enxuto das respostas do MCP (spec, seção 5.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.links import url_da_oportunidade
from ..models.como_conheceu import ComoConheceu
from ..models.etapa_kanban import EtapaKanban
from ..models.motivo_cancelamento import MotivoCancelamento
from ..models.produto import Produto
from ..models.usuario import Usuario

_TIPO_FECHAMENTO = {0: "recorrencia", 1: "projeto"}


@dataclass
class Nomes:
    etapas: dict[int, tuple[str, str]] = field(default_factory=dict)
    usuarios: dict[int, str] = field(default_factory=dict)
    produtos: dict[int, str] = field(default_factory=dict)
    origens: dict[int, str] = field(default_factory=dict)
    motivos: dict[int, str] = field(default_factory=dict)


def _ids(itens: Iterable[Any], atributo: str) -> set[int]:
    return {v for v in (getattr(i, atributo, None) for i in itens) if v is not None}


def _mapa(db: Session, col_id, col_nome, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {i: n for i, n in db.execute(select(col_id, col_nome).where(col_id.in_(ids))).all()}


def carregar_nomes(db: Session, oportunidades: Iterable[Any]) -> Nomes:
    oportunidades = list(oportunidades)
    nomes = Nomes()
    etapas = _ids(oportunidades, "opoEtkId")
    if etapas:
        nomes.etapas = {
            i: (n, p)
            for i, n, p in db.execute(
                select(EtapaKanban.etkId, EtapaKanban.etkNome, EtapaKanban.etkPipeline).where(
                    EtapaKanban.etkId.in_(etapas)
                )
            ).all()
        }
    nomes.usuarios = _mapa(db, Usuario.usuId, Usuario.usuNome, _ids(oportunidades, "opoUsuResponsavelId"))
    nomes.produtos = _mapa(db, Produto.proId, Produto.proNome, _ids(oportunidades, "opoProId"))
    nomes.origens = _mapa(db, ComoConheceu.ccoId, ComoConheceu.ccoNome, _ids(oportunidades, "opoCcoId"))
    nomes.motivos = _mapa(db, MotivoCancelamento.mcaId, MotivoCancelamento.mcaNome, _ids(oportunidades, "opoMcaId"))
    return nomes


def carregar_autores(db: Session, historicos: Iterable[Any]) -> dict[int, str]:
    return _mapa(db, Usuario.usuId, Usuario.usuNome, _ids(list(historicos), "ophUsuId"))


def _data(valor: date | datetime | None) -> str | None:
    return valor.isoformat() if valor is not None else None


def _num(valor: Any) -> float | None:
    return float(valor) if valor is not None else None


def _ref(mapa: dict[int, str], id_: int | None) -> dict | None:
    if id_ is None:
        return None
    return {"id": id_, "nome": mapa.get(id_)}


def _etapa(nomes: Nomes, etk_id: int | None) -> dict | None:
    if etk_id is None:
        return None
    nome, pipeline = nomes.etapas.get(etk_id, (None, None))
    return {"id": etk_id, "nome": nome, "pipeline": pipeline}


def status_de(opo: Any) -> str:
    return opo.opoStatusFechamento or "ativo"


def resumo_oportunidade(opo: Any, nomes: Nomes) -> dict:
    return {
        "id": opo.opoId,
        "titulo": opo.opoTitulo,
        "contato": opo.opoNomeContato,
        "empresa": opo.opoEmpresaContato,
        "status": status_de(opo),
        "etapa": _etapa(nomes, opo.opoEtkId),
        "responsavel": _ref(nomes.usuarios, opo.opoUsuResponsavelId),
        "temperatura": opo.opoTemperatura,
        "lead_score": opo.opoLeadScore,
        "valor": _num(opo.opoValorOportunidade),
        "data_ultimo_contato": _data(opo.opoDataUltimoContato),
    }


def oportunidade_completa(opo: Any, nomes: Nomes) -> dict:
    dados = {
        **resumo_oportunidade(opo, nomes),
        "email": opo.opoEmail,
        "telefone": opo.opoTelefone,
        "solucao": opo.opoSolucao,
        "produto": _ref(nomes.produtos, opo.opoProId),
        "origem": _ref(nomes.origens, opo.opoCcoId),
        "motivo_perda": _ref(nomes.motivos, opo.opoMcaId),
        "reuniao_confirmada": opo.opoReuniaoConfirmada,
        "proposta_enviada": opo.opoPropostaEnviada,
        "receita_pontual": opo.opoReceitaPontual,
        "data_recebimento": _data(opo.opoDataRecebimento),
        "dores": opo.opoDoresMotivadores,
        "comentarios": opo.opoComentarios,
        "origem_externa": {
            "sistema": getattr(opo, "opoOrigemSistema", None),
            "utm_source": getattr(opo, "opoUtmSource", None),
            "utm_campaign": getattr(opo, "opoUtmCampaign", None),
        },
        "criado_em": _data(opo.opoDataCriacao),
        "atualizado_em": _data(opo.opoDataAtualizacao),
        "url": url_da_oportunidade(opo.opoId),
    }
    if status_de(opo) != "ativo":
        dados["fechamento"] = {
            "data": _data(opo.opoDataFechamento),
            "tipo": _TIPO_FECHAMENTO.get(opo.opoFechadoRecorrencia),
            "valor": _num(opo.opoValorFechado),
        }
    return dados


def historico_item(h: Any, autores: dict[int, str]) -> dict:
    return {
        "id": h.ophId,
        "data": _data(h.ophDataRegistro),
        "autor": _ref(autores, h.ophUsuId),
        "conteudo": h.ophConteudo,
    }
