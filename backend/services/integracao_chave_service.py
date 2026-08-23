"""
Emissão, verificação e revogação de chaves de API das integrações externas.

A chave em texto puro existe apenas no instante da criação: é devolvida uma única vez
para quem a criou e nunca mais pode ser recuperada.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import timedelta
from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.tempo import utcnow
from ..exceptions import BadRequestError, NotFoundError
from ..models.integracao_chave import IntegracaoChave

PREFIXO_LITERAL = "sdcrm"
_FORMATO_CHAVE = re.compile(r"^(sdcrm_[0-9a-f]{12})_([A-Za-z0-9_-]{43})$")
_FORMATO_PREFIXO = re.compile(r"^sdcrm_[0-9a-f]{12}$")

ESCOPOS_CONHECIDOS = ("leads:write", "webhooks:read", "mcp:read", "mcp:write")

# Intervalo mínimo entre duas gravações de ichUltimoUsoEm, para o caminho quente
# não pagar um UPDATE por requisição.
_INTERVALO_REGISTRO_USO = timedelta(minutes=5)

# Hash de comparação para o caso "prefixo não existe": mantém o tempo de resposta
# parecido com o do caminho válido, para não denunciar quais prefixos existem.
_HASH_INEXISTENTE = "0" * 64


def _pepper() -> bytes:
    valor = (settings.API_KEY_PEPPER or "").strip()
    if not valor:
        if (settings.APP_ENV or "").strip().lower() == "production":
            raise RuntimeError(
                "API_KEY_PEPPER não configurado. Defina-o no .env antes de emitir ou "
                "validar chaves de API em produção."
            )
        valor = "sdcrm-dev-pepper-nao-use-em-producao"
    return valor.encode("utf-8")


def calcular_hash(chave_plana: str) -> str:
    """
    HMAC-SHA256(pepper, chave) em hex.

    Deliberadamente NÃO é bcrypt/argon2: o segredo tem 256 bits vindos de CSPRNG, então
    não há ataque de dicionário a desacelerar, e um KDF lento custaria ~100 ms em toda
    requisição de integração. É a mesma postura que GitHub e Stripe usam para tokens
    de máquina.
    """
    return hmac.new(_pepper(), chave_plana.encode("utf-8"), hashlib.sha256).hexdigest()


def gerar_chave() -> tuple[str, str, str]:
    """Devolve (chave_plana, prefixo, hash). A chave plana não é persistida."""
    prefixo = f"{PREFIXO_LITERAL}_{secrets.token_hex(6)}"
    chave_plana = f"{prefixo}_{secrets.token_urlsafe(32)}"
    return chave_plana, prefixo, calcular_hash(chave_plana)


def extrair_prefixo(valor: str | None) -> str | None:
    """Prefixo público da chave apresentada, ou None se o formato não bate."""
    if not valor:
        return None
    m = _FORMATO_CHAVE.match(valor.strip())
    return m.group(1) if m else None


def prefixo_para_log(valor: str | None) -> str:
    """
    O que pode ser gravado no log a respeito da chave apresentada.

    Nunca o segredo -- só o prefixo, e apenas quando ele tem o formato esperado.
    """
    prefixo = extrair_prefixo(valor)
    if prefixo:
        return prefixo
    if valor and _FORMATO_PREFIXO.match(valor.strip()):
        return valor.strip()
    return "(malformado)"


def autenticar(db: Session, valor_header: str | None) -> IntegracaoChave | None:
    """
    Resolve a chave apresentada, ou None.

    Devolve None indistintamente para header ausente, malformado, inexistente, com
    segredo errado, revogado, inativo ou expirado: quem chama responde 401 sem revelar
    qual das condições falhou.
    """
    prefixo = extrair_prefixo(valor_header)
    if prefixo is None:
        return None

    chave = db.scalars(
        select(IntegracaoChave).where(IntegracaoChave.ichPrefixo == prefixo)
    ).first()

    if chave is None:
        # Gasta o mesmo trabalho do caminho válido antes de desistir.
        hmac.compare_digest(calcular_hash(valor_header or ""), _HASH_INEXISTENTE)
        return None

    if not hmac.compare_digest(chave.ichHashSecret, calcular_hash(valor_header or "")):
        return None

    if not chave.ichAtivo or chave.ichRevogadaEm is not None:
        return None
    if chave.ichExpiraEm is not None and chave.ichExpiraEm <= utcnow():
        return None
    return chave


def registrar_uso(db: Session, chave: IntegracaoChave) -> None:
    """Atualiza ichUltimoUsoEm no máximo uma vez a cada 5 minutos. Não commita."""
    agora = utcnow()
    if chave.ichUltimoUsoEm is not None and agora - chave.ichUltimoUsoEm < _INTERVALO_REGISTRO_USO:
        return
    chave.ichUltimoUsoEm = agora
    db.add(chave)


def normalizar_escopos(escopos: list[str] | None) -> str:
    pedidos = {e.strip() for e in (escopos or []) if e and e.strip()}
    if not pedidos:
        return "leads:write"
    desconhecidos = sorted(pedidos - set(ESCOPOS_CONHECIDOS))
    if desconhecidos:
        raise BadRequestError(f"Escopo(s) desconhecido(s): {', '.join(desconhecidos)}")
    # Ordena pelo catálogo para o CSV gravado ficar estável entre chamadas.
    return ",".join(e for e in ESCOPOS_CONHECIDOS if e in pedidos)


def tem_escopo(chave: IntegracaoChave, escopo: str) -> bool:
    return escopo in {e.strip() for e in (chave.ichEscopos or "").split(",")}


def listar_chaves(
    db: Session,
    company_id: Optional[int] = None,
    status: Literal["ativos", "inativos", "todos"] = "ativos",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[IntegracaoChave], int]:
    stmt = select(IntegracaoChave)
    if company_id is not None:
        stmt = stmt.where(IntegracaoChave.ichEmpId == company_id)
    if status == "ativos":
        stmt = stmt.where(IntegracaoChave.ichAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(IntegracaoChave.ichAtivo.is_(False))
    stmt = stmt.order_by(IntegracaoChave.ichDataCriacao.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt).all()), total


def get_chave(db: Session, ich_id: int, company_id: Optional[int] = None) -> IntegracaoChave:
    stmt = select(IntegracaoChave).where(IntegracaoChave.ichId == ich_id)
    if company_id is not None:
        stmt = stmt.where(IntegracaoChave.ichEmpId == company_id)
    chave = db.scalars(stmt).first()
    if chave is None:
        raise NotFoundError("Chave de integração não encontrada")
    return chave


def criar_chave(
    db: Session,
    *,
    company_id: int,
    nome: str,
    descricao: str | None = None,
    escopos: list[str] | None = None,
    usu_responsavel_padrao_id: int | None = None,
    expira_em=None,
    criada_usu_id: int | None = None,
) -> tuple[IntegracaoChave, str]:
    """Devolve (registro, chave_plana). A chave plana só existe aqui -- exiba uma vez."""
    chave_plana, prefixo, hash_secret = gerar_chave()
    registro = IntegracaoChave(
        ichEmpId=company_id,
        ichNome=nome.strip(),
        ichDescricao=(descricao or None),
        ichPrefixo=prefixo,
        ichHashSecret=hash_secret,
        ichEscopos=normalizar_escopos(escopos),
        ichUsuResponsavelPadraoId=usu_responsavel_padrao_id,
        ichExpiraEm=expira_em,
        ichCriadaUsuId=criada_usu_id,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro, chave_plana


def revogar_chave(
    db: Session, ich_id: int, company_id: Optional[int], revogada_usu_id: int | None
) -> IntegracaoChave:
    chave = get_chave(db, ich_id, company_id)
    if chave.ichRevogadaEm is None:
        chave.ichRevogadaEm = utcnow()
        chave.ichRevogadaUsuId = revogada_usu_id
    chave.ichAtivo = False
    db.add(chave)
    db.commit()
    db.refresh(chave)
    return chave
