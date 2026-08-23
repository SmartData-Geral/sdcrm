"""
Catalogo de eventos de saida. Fonte unica de verdade, exposta ao frontend por
GET /api/webhooks/eventos para que a UI nunca liste um evento que o backend nao emite.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Evento:
    id: str
    prioridade: str
    rotulo: str
    descricao: str
    disponivel: bool = True
    motivo_indisponivel: str | None = None


# REGRA DE MODELAGEM, ler antes de mexer: neste CRM um lead e um deal sao a MESMA linha
# de `oportunidade`. Por isso lead.created e deal.created sao mutuamente exclusivos e
# discriminados pela origem (opoIchId preenchido => veio da integracao => lead). Sem essa
# regra toda oportunidade nova dispararia os dois e dobraria o consumo de tasks do Zapier.
CATALOGO: tuple[Evento, ...] = (
    Evento("lead.created", "P0", "Lead criado", "Lead entrou pela API de integracao."),
    Evento("lead.updated", "P1", "Lead atualizado", "Lead ja existente foi atualizado pela API."),
    Evento("deal.created", "P1", "Oportunidade criada", "Oportunidade criada pela tela do CRM."),
    Evento("deal.stage_changed", "P0", "Mudou de etapa", "Oportunidade mudou de etapa no funil."),
    Evento("deal.won", "P0", "Ganha", "Oportunidade marcada como ganha."),
    Evento("deal.lost", "P1", "Perdida", "Oportunidade marcada como perdida."),
    Evento("deal.standby", "P3", "Stand-by", "Oportunidade colocada em stand-by."),
    Evento(
        "deal.contact_updated",
        "P2",
        "Contato alterado",
        "Nome, e-mail, telefone ou empresa do contato mudou.",
    ),
    Evento(
        "task.completed",
        "P2",
        "Tarefa concluida",
        "Previsto no catalogo original, mas nao emitido.",
        disponivel=False,
        motivo_indisponivel=(
            "Este CRM nao possui modulo de tarefas. O evento fica reservado e passa a "
            "ser emitido quando a entidade existir."
        ),
    ),
)

POR_ID = {e.id: e for e in CATALOGO}
DISPONIVEIS = frozenset(e.id for e in CATALOGO if e.disponivel)


def existe(evento_id: str) -> bool:
    return evento_id in POR_ID


def disponivel(evento_id: str) -> bool:
    return evento_id in DISPONIVEIS


def validar_lista(eventos: list[str] | None) -> list[str]:
    """Normaliza a lista de uma assinatura. '*' assina tudo o que esta disponivel."""
    from ..exceptions import BadRequestError

    pedidos = [e.strip() for e in (eventos or []) if e and e.strip()]
    if not pedidos or pedidos == ["*"]:
        return sorted(DISPONIVEIS)

    desconhecidos = sorted(set(pedidos) - set(POR_ID))
    if desconhecidos:
        raise BadRequestError("Evento(s) desconhecido(s): " + ", ".join(desconhecidos))

    indisponiveis = sorted(set(pedidos) - DISPONIVEIS)
    if indisponiveis:
        detalhes = "; ".join(
            e + ": " + (POR_ID[e].motivo_indisponivel or "indisponivel") for e in indisponiveis
        )
        raise BadRequestError("Evento(s) ainda nao disponivel(is) -- " + detalhes)

    return sorted(set(pedidos))
