"""
Catálogo de macros {{chave}} usadas nos textos de modelos/cláusulas de contrato.

Manter as chaves alinhadas com:
- contrato_service._build_placeholders_values
- contrato_render_service._placeholder_values
"""

from __future__ import annotations

# Ordem estável para exibição na UI / documentação.
_MACRO_ROWS: tuple[dict[str, str], ...] = (
    {
        "key": "razao_social",
        "titulo": "Razão social",
        "descricao": "Razão social da contratante (cadastro do contrato).",
    },
    {
        "key": "cnpj",
        "titulo": "CNPJ",
        "descricao": "CNPJ da contratante.",
    },
    {
        "key": "endereco",
        "titulo": "Endereço",
        "descricao": "Endereço completo da contratante.",
    },
    {
        "key": "responsavel_nome",
        "titulo": "Responsável (nome)",
        "descricao": "Nome do representante legal da contratante.",
    },
    {
        "key": "responsavel_cpf",
        "titulo": "Responsável (CPF)",
        "descricao": "CPF do representante legal da contratante.",
    },
    {
        "key": "objeto_contrato",
        "titulo": "Objeto do contrato",
        "descricao": "Descrição do objeto contratual.",
    },
    {
        "key": "valor_contrato",
        "titulo": "Valor do contrato",
        "descricao": (
            "Valor principal. No texto de cláusulas costuma aparecer como número simples; "
            "no HTML/PDF gerado pode aparecer formatado em reais (R$)."
        ),
    },
    {
        "key": "valor_manutencao",
        "titulo": "Valor da manutenção",
        "descricao": "Valor da manutenção (formato monetário conforme o contexto de renderização).",
    },
    {
        "key": "data_inicio",
        "titulo": "Data de início",
        "descricao": (
            "Data de início do contrato. No texto de cláusulas costuma ser ISO (AAAA-MM-DD); "
            "no HTML/PDF pode aparecer como dd/mm/aaaa."
        ),
    },
    {
        "key": "prazo_conclusao",
        "titulo": "Prazo de conclusão",
        "descricao": "Texto livre do prazo (ex.: “90 (noventa) dias”).",
    },
    {
        "key": "dias_pagamento",
        "titulo": "Dias para o primeiro pagamento",
        "descricao": "Número de dias corridos após a assinatura para o primeiro pagamento.",
    },
    {
        "key": "dias_antecedencia_rescisao",
        "titulo": "Dias de antecedência para rescisão",
        "descricao": "Prazo de aviso prévio para rescisão ou redução de plano, em dias.",
    },
    {
        "key": "horas_melhorias_mensais",
        "titulo": "Horas de melhorias mensais",
        "descricao": "Quantidade inteira de horas de melhorias mensais previstas no contrato.",
    },
)


def list_macro_catalog() -> list[dict[str, str]]:
    return [dict(row) for row in _MACRO_ROWS]
