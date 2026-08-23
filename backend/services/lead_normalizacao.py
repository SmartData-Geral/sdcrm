"""
Normalização de contato para deduplicação de leads.

Funções puras: sem sessão de banco, sem I/O e sem dependência externa. É isso que
permite testá-las no estilo do projeto (unittest, sem fixture de banco) e copiá-las
para dentro de uma migration de backfill sem arrastar a aplicação junto.

Forma canônica de telefone: dígitos E.164 **sem** o "+", sempre com DDI, e sempre
com o 9º dígito nos celulares brasileiros -> "5541999990000".
"""

from __future__ import annotations

import re
import unicodedata

DDI_BRASIL = "55"

_SO_DIGITOS = re.compile(r"\D+")
_EMAIL_BASICO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SLUG_INVALIDO = re.compile(r"[^a-z0-9]+")
_SLUG_ACEITO = re.compile(r"^[a-z0-9_]{2,60}$")

# Primeiro dígito do assinante que caracteriza celular no Brasil.
# Fixos começam em 2-5 e nunca recebem o 9º dígito.
_INICIAIS_CELULAR = frozenset("6789")


def normalizar_email(valor: str | None) -> str | None:
    """
    Devolve o e-mail em minúsculas e sem espaços, ou None quando não for utilizável
    para deduplicar (vazio ou malformado).

    Não removemos pontos nem sufixos "+tag" do Gmail de propósito: seria surpreendente
    e fundiria contatos legitimamente distintos.
    """
    if valor is None:
        return None
    texto = unicodedata.normalize("NFKC", str(valor)).strip().lower()
    if not texto or len(texto) > 255 or not _EMAIL_BASICO.match(texto):
        return None
    return texto


def normalizar_telefone(valor: str | None) -> str | None:
    """
    Devolve o telefone na forma canônica, ou None quando o número não é confiável
    o bastante para deduplicar.

    Retornar None é uma decisão de projeto, não uma falha: um número sem DDD como
    "9999-0000" casaria com meio Brasil, então ele é gravado em opoTelefone mas fica
    fora do dedup.
    """
    if valor is None:
        return None
    bruto = str(valor).strip()
    if not bruto:
        return None

    internacional_explicito = bruto.startswith("+")
    digitos = _SO_DIGITOS.sub("", bruto)
    if not digitos:
        return None

    # "00" é prefixo de discagem internacional, equivalente ao "+".
    if digitos.startswith("00") and len(digitos) > 12:
        digitos = digitos[2:]
        internacional_explicito = True

    # Número estrangeiro declarado: preservamos como veio, sem as regras brasileiras.
    if internacional_explicito and not digitos.startswith(DDI_BRASIL):
        return digitos[:20] if 8 <= len(digitos) <= 20 else None

    # A ordem importa: 10/11 dígitos é nacional COM DDD, e o DDD 55 (Santa Maria/RS)
    # existe de verdade. Testar o comprimento antes do prefixo evita tratar
    # "5532223333" como DDI+número truncado.
    if len(digitos) in (10, 11):
        nacional = digitos
    elif len(digitos) in (12, 13) and digitos.startswith(DDI_BRASIL):
        nacional = digitos[2:]
    else:
        return None

    canonico = _canonizar_nacional(nacional)
    return None if canonico is None else DDI_BRASIL + canonico


def _canonizar_nacional(nacional: str) -> str | None:
    """DDD + assinante, inserindo o 9º dígito quando o assinante é celular legado."""
    ddd, assinante = nacional[:2], nacional[2:]
    if not ddd.isdigit() or int(ddd) < 11:
        return None
    if not assinante or assinante[0] == "0":
        return None
    if len(assinante) == 8 and assinante[0] in _INICIAIS_CELULAR:
        assinante = "9" + assinante
    return ddd + assinante


def variantes_telefone(canonico: str | None) -> set[str]:
    """
    Formas equivalentes do mesmo número, para o dedup consultar com IN (...).

    Cobre registros gravados antes da canonicalização do 9º dígito: o mesmo celular
    pode estar no banco como 5541999990000 ou como 554199990000.
    """
    if not canonico:
        return set()
    formas = {canonico}
    if canonico.startswith(DDI_BRASIL):
        assinante = canonico[4:]
        if len(assinante) == 9 and assinante[0] == "9":
            formas.add(canonico[:4] + assinante[1:])
    return formas


def slugificar(valor: str | None) -> str | None:
    """"Planilha de Leads" -> "planilha_de_leads". Usado para casar `source` com como_conheceu."""
    if valor is None:
        return None
    sem_acento = unicodedata.normalize("NFKD", str(valor))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    slug = _SLUG_INVALIDO.sub("_", sem_acento.strip().lower()).strip("_")
    return slug or None


def origem_aceitavel(slug: str | None) -> bool:
    """Guarda contra `source` lixo criar linhas em como_conheceu indefinidamente."""
    return bool(slug and _SLUG_ACEITO.match(slug))


def rotular_origem(slug: str) -> str:
    """"planilha_leads" -> "Planilha Leads", para o nome exibido em como_conheceu."""
    return " ".join(parte.capitalize() for parte in slug.split("_") if parte)[:200]
