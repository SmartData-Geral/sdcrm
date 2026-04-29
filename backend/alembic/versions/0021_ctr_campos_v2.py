"""Contrato: remove forma/vigencia/foro/reajuste do cadastro; add prazo e dias comerciais

Revision ID: 0021_ctr_campos_v2
Revises: 0020_contrato_tpl_smartdata
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0021_ctr_campos_v2"
down_revision: str | None = "0020_contrato_tpl_smartdata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SMART_MODELO = "Prestação de Serviços - Smart Data (Checking)"


CLAUSULA_4_TEXTO = """4.1. Em contrapartida aos serviços prestados pela CONTRATADA, a CONTRATANTE efetuará o pagamento de R$ {{valor_contrato}} mensais. Os pagamentos iniciarão {{dias_pagamento}} dias corridos após a assinatura do contrato e serão efetuados mediante transferência bancária, PIX ou outro meio de pagamento combinado entre as Partes, em conta a ser indicada pela CONTRATADA.

Parágrafo Primeiro:

O valor estabelecido no caput será reajustado anualmente pelo IPCA acumulado, considerando como data base a data de início deste contrato.

Parágrafo Segundo:

Caso os pagamentos não ocorram no prazo estipulado acima, ocorrerá a aplicação de 2% (dois por cento) de multa sobre o valor da retribuição mensal, mais 1% (um por cento) de juros ao mês, ou fração, calculados pro rata die entre a data do vencimento e a data do efetivo pagamento.

Parágrafo Terceiro:

Caso a CONTRATADA esteja inadimplente com quaisquer de suas obrigações contratuais, a CONTRATANTE a notificará, por escrito, para regularizar a situação em até 7 (sete) dias; após este prazo, caso mantida a irregularidade, a CONTRATANTE poderá, sem que se configure inadimplemento ou violação a este instrumento, suspender os pagamentos à CONTRATADA."""

CLAUSULA_7_TEXTO = """7.1. Fica estipulado à CONTRATADA o prazo de {{prazo_conclusao}} para a entrega e conclusão da primeira versão funcional da aplicação conforme descrição na Cláusula Primeira (Objeto), ao CONTRATANTE, a contar a partir da reunião de briefing e alinhamento a ser acordada entre as partes."""

CLAUSULA_8_TEXTO = """8.1. O presente contrato vigorará a partir de {{data_inicio}}, por prazo indeterminado, todavia permanecerá condicionado à assinatura deste instrumento e à resolução mediante o fiel cumprimento das obrigações aqui assumidas por ambas as partes."""

CLAUSULA_9_TEXTO = """9.1. O presente contrato poderá ser rescindido por qualquer uma das PARTES sem quaisquer ônus, mediante notificação escrita à parte contrária com antecedência mínima de {{dias_antecedencia_rescisao}} dias.

9.2. O presente contrato poderá ser alterado consensualmente pelas Partes, por meio de termo aditivo, que deverá ser anexado ao presente.

9.3. Quaisquer leis, decretos, portarias, tributos, impostos, contribuições, convenções ou encargos legais aplicáveis ao Contrato, que forem criados, alterados ou extintos após a data base contratual, que venham impactar no preço da prestação de serviços ou provocar o desequilíbrio econômico-financeiro do contrato, deverão ser considerados pelas Partes, promovendo-se os ajustes necessários nos parâmetros e condições contratuais diretamente afetados, de forma a serem considerados nos faturamentos correspondentes, tão logo vigorarem.

9.4. O presente contrato poderá ser rescindido, a qualquer momento, caso alguma das Partes não cumpra as obrigações descritas, resguardando-se o direito a receber, de maneira proporcional, a contraprestação pelos serviços prestados, bem como qualquer tipo de indenização pelo não cumprimento do acordado.

9.5. O presente contrato poderá ser rescindido de imediato, independentemente de qualquer notificação judicial ou extrajudicial, nas seguintes hipóteses:

• Falência, recuperação judicial ou dissolução de qualquer uma das Partes; e

• Quando da utilização de mão de obra infantil ou trabalho irregular de adolescentes.

9.6. A CONTRATANTE pode reduzir o plano a qualquer momento, mediante aviso prévio com antecedência de {{dias_antecedencia_rescisao}} dias. A redução de horas e valores deverá ser acordada com a CONTRATADA, respeitando a política comercial vigente no momento da solicitação.

9.7. Caso a CONTRATANTE decida não contratar mais horas de melhorias mensais, é necessário informar a CONTRATADA com {{dias_antecedencia_rescisao}} dias de antecedência. Nesse caso, apenas o valor de manutenção de R$ {{valor_manutencao}} será cobrado, o qual contempla hospedagem, licenças, manutenção e backup."""

CLAUSULA_11_TEXTO = """11.1. As Partes elegem o foro da Comarca de Curitiba, Estado do Paraná, para dirimir quaisquer controvérsias oriundas deste contrato, renunciando a qualquer outro, por mais privilegiado que seja.

As Partes assim justos e contratantes assinam o presente instrumento em duas vias de igual teor e forma.

Curitiba, {{data_inicio}}.

Espelhos de assinatura (assinaturas manuscritas nas vias físicas quando aplicável):

Contratada — SMART DATA SOLUÇÕES DIGITAIS LTDA. — CNPJ 33.015.778/0001-23 — Representante: Carlos H. Bomfim de Souza

Contratante — {{razao_social}} — CNPJ {{cnpj}} — Representante: {{responsavel_nome}} — CPF {{responsavel_cpf}}"""


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("contrato")}

    # Se o DDL já foi aplicado em tentativa anterior (erro apenas no alembic_version), não repete ALTER.
    if "ctrFormaPagamento" in cols:
        op.add_column(
            "contrato",
            sa.Column(
                "ctrPrazoConclusao",
                sa.String(length=200),
                nullable=False,
                server_default="90 (noventa) dias",
            ),
        )
        op.add_column(
            "contrato",
            sa.Column(
                "ctrDiasPagamento",
                sa.Integer(),
                nullable=False,
                server_default="30",
            ),
        )
        op.add_column(
            "contrato",
            sa.Column(
                "ctrDiasAntecedenciaRescisao",
                sa.Integer(),
                nullable=False,
                server_default="30",
            ),
        )
        op.add_column(
            "contrato",
            sa.Column(
                "ctrValorManutencao",
                sa.Numeric(14, 2),
                nullable=False,
                server_default="390.00",
            ),
        )

        op.alter_column("contrato", "ctrPrazoConclusao", server_default=None)
        op.alter_column("contrato", "ctrDiasPagamento", server_default=None)
        op.alter_column("contrato", "ctrDiasAntecedenciaRescisao", server_default=None)
        op.alter_column("contrato", "ctrValorManutencao", server_default=None)

        op.drop_column("contrato", "ctrFormaPagamento")
        op.drop_column("contrato", "ctrVigencia")
        op.drop_column("contrato", "ctrForo")
        op.drop_column("contrato", "ctrReajuste")

    conn = bind
    ctm = conn.execute(
        sa.text("SELECT ctmId FROM contrato_modelo WHERE ctmEmpId = 1 AND ctmNome = :n"),
        {"n": SMART_MODELO},
    ).scalar()
    if ctm is None:
        return

    updates = [
        (4, CLAUSULA_4_TEXTO),
        (7, CLAUSULA_7_TEXTO),
        (8, CLAUSULA_8_TEXTO),
        (9, CLAUSULA_9_TEXTO),
        (11, CLAUSULA_11_TEXTO),
    ]
    for ordem, texto in updates:
        conn.execute(
            sa.text(
                "UPDATE contrato_modelo_clausula SET cmcTextoPadrao = :tx "
                "WHERE cmcCtmId = :ctm AND cmcOrdem = :ord"
            ),
            {"tx": texto, "ctm": ctm, "ord": ordem},
        )


def downgrade() -> None:
    op.add_column(
        "contrato",
        sa.Column("ctrFormaPagamento", sa.String(length=200), nullable=False, server_default=""),
    )
    op.add_column(
        "contrato",
        sa.Column("ctrVigencia", sa.String(length=200), nullable=False, server_default=""),
    )
    op.add_column(
        "contrato",
        sa.Column("ctrForo", sa.String(length=200), nullable=False, server_default="Curitiba/PR"),
    )
    op.add_column("contrato", sa.Column("ctrReajuste", sa.Text(), nullable=True))

    op.alter_column("contrato", "ctrFormaPagamento", server_default=None)
    op.alter_column("contrato", "ctrVigencia", server_default=None)
    op.alter_column("contrato", "ctrForo", server_default=None)

    op.drop_column("contrato", "ctrPrazoConclusao")
    op.drop_column("contrato", "ctrDiasPagamento")
    op.drop_column("contrato", "ctrDiasAntecedenciaRescisao")
    op.drop_column("contrato", "ctrValorManutencao")
