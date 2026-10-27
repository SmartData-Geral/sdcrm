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
from ...models.meta_ads_cockpit_leitura import MetaAdsCockpitLeitura
from ...schemas.meta_ads import (
    MetaAdsCockpitLeituraResponse,
    MetaAdsCockpitLeituraTexto,
    MetaAdsCockpitResponse,
    MetaAdsLinha,
)
from . import cockpit
from .indicadores import FiltroPainel
from .resumo import PREFIXO_AVISO, _motivo

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
