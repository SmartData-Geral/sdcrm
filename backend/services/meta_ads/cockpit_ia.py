"""Leitura do analista (IA) do cockpit de campanhas e o contexto agregado que a IA recebe.

`contexto_ia` so tem numeros, nomes de campanha/anuncio, selos e quadrantes: nunca `revisaoOrigem`,
nome, telefone ou e-mail de lead (`operacao.origemRevisar` e so uma contagem). O mesmo contexto
alimenta a leitura, o chat e a ferramenta MCP. A leitura e guardada por recorte (empresa, datas,
conta, filtro de ativas) com a impressao digital do contexto: se os numeros ou as metas mudam,
ela aparece como desatualizada.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.tempo import utcnow
from ...exceptions import BadRequestError, TooManyRequestsError
from ...models.meta_ads_cockpit_leitura import MetaAdsCockpitLeitura
from ...models.meta_ads_pergunta_uso import MetaAdsPerguntaUso
from ...schemas.meta_ads import (
    MetaAdsCockpitLeituraResponse,
    MetaAdsCockpitLeituraTexto,
    MetaAdsCockpitResponse,
    MetaAdsLinha,
    MetaAdsPerguntaMensagem,
    MetaAdsPerguntaResponse,
)
from . import cockpit
from .indicadores import FiltroPainel
from .resumo import PREFIXO_AVISO, _motivo, hoje_local

logger = logging.getLogger(__name__)

MAX_CRIATIVOS = 30
CHAVES_LEITURA = ("manchete", "funciona", "problema", "olharAgora")
_SEM_IDENTIFICACAO = {"filhos", "id", "mcgId", "nivel", "macId", "nome", "status"}

PROMPT_LEITURA = (
    "Você é um analista de mídia paga que explica os resultados de campanhas Meta Ads para quem não "
    "é da área. Escreva em português simples, sem jargão, em frases curtas. "
    "Use apenas os números recebidos; não invente valores nem compare com referências externas, "
    "médias de mercado ou benchmarks. "
    "Quando um criativo ou etapa tiver amostra pequena (poucos leads no CRM), avise que a conclusão "
    "ainda é fraca. "
    "Recomende o que verificar ou testar; nunca diga que vai agir, alterar, pausar ou escalar algo "
    "na conta. "
    "Responda somente com um JSON, sem texto fora dele, neste formato: "
    '{"manchete": "uma frase com o veredito do período e o porquê", '
    '"funciona": "o que está funcionando, em até duas frases", '
    '"problema": "onde está o problema, em até duas frases", '
    '"olharAgora": "o que verificar agora, em até duas frases"}.'
)


LIMITE_PERGUNTAS_DIA = 30
MAX_HISTORICO = 12
MAX_TEXTO_HISTORICO = 2000
PAPEIS_HISTORICO = {"pergunta": "user", "resposta": "assistant"}

PROMPT_PERGUNTA = (
    "Você é um analista de mídia paga que responde perguntas sobre os resultados de campanhas Meta Ads "
    "para quem não é da área. Responda em português simples, sem jargão, em poucas frases. "
    "Use apenas os números do período recebidos abaixo; não invente valores nem compare com referências "
    "externas, médias de mercado ou benchmarks. "
    "Quando um criativo ou etapa tiver amostra pequena (poucos leads no CRM), avise que a conclusão "
    "ainda é fraca. "
    "Recomende o que verificar ou testar; nunca diga que vai agir, alterar, pausar ou escalar algo "
    "na conta. "
    "Se a pergunta não puder ser respondida com estes números, diga isso e sugira o que olhar. "
    "Mantenha a resposta curta."
)


def _numeros(linha: MetaAdsLinha) -> dict:
    return linha.model_dump(mode="json", exclude=_SEM_IDENTIFICACAO)


def contexto_ia(c: MetaAdsCockpitResponse) -> dict:
    """Contexto agregado do cockpit para a IA e para o MCP, sem dados pessoais."""
    criativos = sorted(c.criativos, key=lambda x: -x.investimento)[:MAX_CRIATIVOS]
    return {
        "periodo": {
            "inicio": c.inicio.isoformat(),
            "fim": c.fim.isoformat(),
            "anteriorInicio": c.anteriorInicio.isoformat(),
            "anteriorFim": c.anteriorFim.isoformat(),
        },
        "metas": c.metas.model_dump(mode="json"),
        "total": _numeros(c.total),
        "anterior": _numeros(c.anterior),
        "anteriorTemDados": c.anteriorTemDados,
        "taxaMql": c.taxaMql,
        "selos": c.selos.model_dump(mode="json"),
        "funil": [e.model_dump(mode="json") for e in c.funil],
        "gargalo": c.gargalo,
        "fraseGargalo": c.fraseGargalo,
        "intervalo": c.intervalo,
        "serie": [p.model_dump(mode="json") for p in c.serie],
        "criativos": [x.model_dump(mode="json") for x in criativos],
        "operacao": c.operacao.model_dump(mode="json"),
    }


def impressao_digital(contexto: dict) -> str:
    texto = json.dumps(contexto, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def interpretar_leitura(texto: str) -> dict | None:
    """Aceita JSON puro ou entre crases; exige as quatro chaves com texto nao vazio."""
    bruto = (texto or "").strip()
    cercado = re.match(r"^```[a-zA-Z]*\s*(.*?)\s*```$", bruto, re.DOTALL)
    if cercado:
        bruto = cercado.group(1)
    try:
        dados = json.loads(bruto)
    except ValueError:
        return None
    if not isinstance(dados, dict):
        return None
    leitura = {}
    for chave in CHAVES_LEITURA:
        valor = dados.get(chave)
        if not isinstance(valor, str) or not valor.strip():
            return None
        leitura[chave] = valor.strip()
    return leitura


def _ia_disponivel() -> bool:
    try:
        from ..llm.llm_factory import get_scope_provider

        get_scope_provider()
        return True
    except Exception:
        return False


def _chave(emp_id: int, filtro: FiltroPainel) -> tuple:
    return (
        MetaAdsCockpitLeitura.mclEmpId == emp_id,
        MetaAdsCockpitLeitura.mclInicio == filtro.data_inicial,
        MetaAdsCockpitLeitura.mclFim == filtro.data_final,
        MetaAdsCockpitLeitura.mclMacId == (filtro.mac_id or 0),
        MetaAdsCockpitLeitura.mclSomenteAtivas == bool(filtro.somente_ativas),
    )


def _buscar(db: Session, emp_id: int, filtro: FiltroPainel) -> MetaAdsCockpitLeitura | None:
    return db.execute(select(MetaAdsCockpitLeitura).where(*_chave(emp_id, filtro))).scalar_one_or_none()


def _resposta(
    guardada: MetaAdsCockpitLeitura | None, digest: str, aviso: str | None, ia_disponivel: bool
) -> MetaAdsCockpitLeituraResponse:
    if guardada is None:
        return MetaAdsCockpitLeituraResponse(
            leitura=None, texto=None, geradoEm=None, desatualizada=False, aviso=aviso,
            iaDisponivel=ia_disponivel,
        )
    conteudo = guardada.mclLeitura or {}
    leitura = conteudo.get("leitura")
    return MetaAdsCockpitLeituraResponse(
        leitura=MetaAdsCockpitLeituraTexto(**leitura) if leitura else None,
        texto=conteudo.get("texto"),
        geradoEm=guardada.mclGeradoEm,
        desatualizada=guardada.mclDigest != digest,
        aviso=aviso,
        iaDisponivel=ia_disponivel,
    )


def obter_leitura(db: Session, emp_id: int, filtro: FiltroPainel) -> MetaAdsCockpitLeituraResponse:
    contexto = contexto_ia(cockpit.montar(db, emp_id, filtro))
    return _resposta(_buscar(db, emp_id, filtro), impressao_digital(contexto), None, _ia_disponivel())


def gerar_leitura(
    db: Session, emp_id: int, filtro: FiltroPainel, *, provedor=None
) -> MetaAdsCockpitLeituraResponse:
    """Gera a leitura do recorte e substitui a guardada. Em erro, mantem a guardada e avisa."""
    contexto = contexto_ia(cockpit.montar(db, emp_id, filtro))
    digest = impressao_digital(contexto)
    guardada = _buscar(db, emp_id, filtro)
    try:
        if provedor is None:
            from ..llm.llm_factory import get_scope_provider

            provedor = get_scope_provider()
        texto = provedor.chat_completion(
            [
                {"role": "system", "content": PROMPT_LEITURA},
                {"role": "user", "content": json.dumps(contexto, ensure_ascii=False)},
            ],
            temperature=0.3,
        )
        texto = (texto or "").strip()
        if not texto:
            raise ValueError("resposta vazia")
    except Exception as exc:
        logger.warning("Cockpit: leitura por IA indisponivel (%s)", type(exc).__name__)
        return _resposta(guardada, digest, f"{PREFIXO_AVISO}: {_motivo(exc)}", _ia_disponivel())

    leitura = interpretar_leitura(texto)
    conteudo = {"leitura": leitura, "texto": None if leitura else texto}
    if guardada is None:
        guardada = MetaAdsCockpitLeitura(
            mclEmpId=emp_id, mclInicio=filtro.data_inicial, mclFim=filtro.data_final,
            mclMacId=filtro.mac_id or 0, mclSomenteAtivas=bool(filtro.somente_ativas),
        )
        db.add(guardada)
    guardada.mclDigest = digest
    guardada.mclLeitura = conteudo
    guardada.mclGeradoEm = utcnow()
    db.commit()
    return _resposta(guardada, digest, None, True)


def filtrar_historico(historico: list[MetaAdsPerguntaMensagem]) -> list[dict]:
    """O historico vem do navegador (nao confiavel): so papeis conhecidos, texto curto, ultimas 12."""
    validas = [
        m for m in historico
        if m.papel in PAPEIS_HISTORICO and m.texto.strip() and len(m.texto) <= MAX_TEXTO_HISTORICO
    ]
    return [{"role": PAPEIS_HISTORICO[m.papel], "content": m.texto} for m in validas[-MAX_HISTORICO:]]


def _uso_do_dia(db: Session, usu_id: int, dia) -> MetaAdsPerguntaUso | None:
    return db.execute(
        select(MetaAdsPerguntaUso).where(
            MetaAdsPerguntaUso.mpuUsuId == usu_id, MetaAdsPerguntaUso.mpuData == dia
        )
    ).scalar_one_or_none()


def perguntar(
    db: Session,
    emp_id: int,
    usu_id: int,
    filtro: FiltroPainel,
    pergunta: str,
    historico: list[MetaAdsPerguntaMensagem],
    *,
    provedor=None,
    hoje=None,
) -> MetaAdsPerguntaResponse:
    """Responde a pergunta com os numeros do recorte; so resposta bem-sucedida conta no limite diario."""
    dia = hoje or hoje_local()
    uso = _uso_do_dia(db, usu_id, dia)
    if uso is not None and uso.mpuQuantidade >= LIMITE_PERGUNTAS_DIA:
        raise TooManyRequestsError("Limite de perguntas de hoje atingido.")

    contexto = contexto_ia(cockpit.montar(db, emp_id, filtro))
    mensagens = [
        {
            "role": "system",
            "content": PROMPT_PERGUNTA + "\n\nNúmeros do período (JSON):\n"
            + json.dumps(contexto, ensure_ascii=False),
        },
        *filtrar_historico(historico),
        {"role": "user", "content": pergunta},
    ]
    try:
        if provedor is None:
            from ..llm.llm_factory import get_scope_provider

            provedor = get_scope_provider()
        texto = (provedor.chat_completion(mensagens, temperature=0.3) or "").strip()
        if not texto:
            raise ValueError("resposta vazia")
    except Exception as exc:
        logger.warning("Cockpit: pergunta por IA indisponivel (%s)", type(exc).__name__)
        raise BadRequestError(f"{PREFIXO_AVISO}: {_motivo(exc)}") from exc

    if uso is None:
        uso = MetaAdsPerguntaUso(mpuUsuId=usu_id, mpuData=dia, mpuQuantidade=0)
        db.add(uso)
    uso.mpuQuantidade += 1
    db.commit()
    return MetaAdsPerguntaResponse(
        resposta=texto, restantesHoje=max(LIMITE_PERGUNTAS_DIA - uso.mpuQuantidade, 0)
    )
