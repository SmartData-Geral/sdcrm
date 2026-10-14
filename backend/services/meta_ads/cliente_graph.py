"""
Cliente minimo da Graph API do Meta, somente leitura (conta, campanhas e insights).

O token vai sempre no cabecalho Authorization, nunca na URL: assim ele nao vaza em log de
proxy, em paging.next nem em mensagem de erro. Erros do Meta viram tres excecoes:
TokenInvalidoErro (parar e pedir token novo), ErroTemporario (limite de chamadas, 5xx ou
rede: retentado com espera crescente) e MetaGraphErro (o resto).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import httpx

from ...config import settings

BASE_URL = "https://graph.facebook.com"
# 190: token invalido/expirado; 102: sessao; 200/10: sem permissao na conta.
CODIGOS_TOKEN = frozenset({190, 102, 200, 10})
CODIGOS_LIMITE = frozenset({4, 17, 32, 613, 80004})
# O Meta reporta o mesmo lead em mais de um tipo; conta-se so o primeiro presente.
TIPOS_LEAD = ("lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead")
ESPERAS_PADRAO = (30, 60, 120)


class MetaGraphErro(Exception):
    def __init__(self, mensagem: str, codigo: int | None = None) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo


class TokenInvalidoErro(MetaGraphErro):
    pass


class ErroTemporario(MetaGraphErro):
    pass


@dataclass(frozen=True)
class ContaMeta:
    nome: str
    moeda: str | None
    fuso: str | None


@dataclass(frozen=True)
class CampanhaMeta:
    id: str
    nome: str
    objetivo: str | None
    status: str | None


@dataclass(frozen=True)
class InsightDia:
    campanha_id: str
    campanha_nome: str
    dia: date
    investimento: Decimal
    impressoes: int
    cliques: int
    alcance: int
    leads: int


def normalizar_conta(valor: str | None) -> str:
    digitos = re.sub(r"\D", "", valor or "")
    if not digitos:
        raise ValueError("Informe o id da conta de anúncios (ex.: act_1234567890)")
    return "act_" + digitos


def _inteiro(valor) -> int:
    if valor in (None, ""):
        return 0
    return int(float(valor))


def extrair_leads(actions: list | None) -> int:
    por_tipo = {a.get("action_type"): a.get("value") for a in actions or []}
    for tipo in TIPOS_LEAD:
        if tipo in por_tipo:
            return _inteiro(por_tipo[tipo])
    return 0


class ClienteGraph:
    def __init__(
        self,
        token: str,
        *,
        versao: str | None = None,
        transporte: httpx.BaseTransport | None = None,
        dormir: Callable[[float], None] = time.sleep,
        esperas: tuple[float, ...] = ESPERAS_PADRAO,
    ) -> None:
        self._token = token
        self._dormir = dormir
        self._esperas = esperas
        self._http = httpx.Client(
            base_url=f"{BASE_URL}/{versao or settings.META_API_VERSION}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60.0,
            transport=transporte,
        )

    def __enter__(self) -> "ClienteGraph":
        return self

    def __exit__(self, *_exc) -> None:
        self._http.close()

    def obter_conta(self, act_id: str) -> ContaMeta:
        dados = self._get(f"/{act_id}", {"fields": "name,currency,timezone_name,account_status"})
        return ContaMeta(
            nome=dados.get("name") or act_id,
            moeda=dados.get("currency"),
            fuso=dados.get("timezone_name"),
        )

    def listar_campanhas(self, act_id: str) -> list[CampanhaMeta]:
        params = {"fields": "id,name,objective,effective_status", "limit": 500}
        return [
            CampanhaMeta(
                id=str(c["id"]),
                nome=c.get("name") or str(c["id"]),
                objetivo=c.get("objective"),
                status=c.get("effective_status"),
            )
            for c in self._paginar(f"/{act_id}/campaigns", params)
        ]

    def listar_insights(self, act_id: str, inicio: date, fim: date) -> list[InsightDia]:
        params = {
            "level": "campaign",
            "time_increment": 1,
            "time_range": json.dumps({"since": inicio.isoformat(), "until": fim.isoformat()}),
            "fields": "campaign_id,campaign_name,spend,impressions,clicks,reach,actions",
            "limit": 500,
        }
        return [
            InsightDia(
                campanha_id=str(linha["campaign_id"]),
                campanha_nome=linha.get("campaign_name") or str(linha["campaign_id"]),
                dia=date.fromisoformat(linha["date_start"]),
                investimento=Decimal(str(linha.get("spend") or "0")),
                impressoes=_inteiro(linha.get("impressions")),
                cliques=_inteiro(linha.get("clicks")),
                alcance=_inteiro(linha.get("reach")),
                leads=extrair_leads(linha.get("actions")),
            )
            for linha in self._paginar(f"/{act_id}/insights", params)
        ]

    def _paginar(self, caminho: str, params: dict) -> Iterator[dict]:
        dados = self._get(caminho, params)
        while True:
            yield from dados.get("data", [])
            proxima = (dados.get("paging") or {}).get("next")
            if not proxima:
                return
            dados = self._get(proxima, None)

    def _get(self, url: str, params: dict | None) -> dict:
        tentativa = 0
        while True:
            try:
                resposta = self._http.get(url, params=params)
            except httpx.TransportError as exc:
                erro: MetaGraphErro = ErroTemporario(
                    f"Falha de rede ao falar com o Meta ({type(exc).__name__})."
                )
            else:
                if resposta.status_code == 200:
                    return resposta.json()
                erro = self._traduzir(resposta)
            if not isinstance(erro, ErroTemporario) or tentativa >= len(self._esperas):
                raise erro
            self._dormir(self._esperas[tentativa])
            tentativa += 1

    def _traduzir(self, resposta: httpx.Response) -> MetaGraphErro:
        try:
            corpo = resposta.json().get("error") or {}
        except ValueError:
            corpo = {}
        codigo = corpo.get("code")
        detalhe = str(corpo.get("message") or f"HTTP {resposta.status_code}")
        detalhe = detalhe.replace(self._token, "***")[:300]
        if codigo in CODIGOS_TOKEN:
            return TokenInvalidoErro(
                "Token inválido, expirado ou sem acesso à conta — gere um novo no "
                f"Business Manager. ({detalhe})",
                codigo,
            )
        if codigo in CODIGOS_LIMITE or resposta.status_code >= 500:
            return ErroTemporario(
                f"Meta indisponível ou limite de chamadas atingido. ({detalhe})", codigo
            )
        return MetaGraphErro(f"Erro do Meta: {detalhe}", codigo)
