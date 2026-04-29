"""Seed modelo Contrato Prestacao Servicos Smart Data (base Checking)

Revision ID: 0020_contrato_tpl_smartdata
Revises: 0019_opo_rec_pontual
Create Date: 2026-04-28

Insere um template `contrato_modelo` para a empresa 1 com cláusulas alinhadas ao
Markdown de referência. Textos sensíveis ao cliente usam placeholders ({{nome}}).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "0020_contrato_tpl_smartdata"
down_revision: str | None = "0019_opo_rec_pontual"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EMP_ID = 1
MODELO_NOME = "Prestação de Serviços - Smart Data (Checking)"
MODELO_DESC = (
    "Template baseado no contrato de prestação de serviços (BI/sistema gerencial); "
    "valores-chave parametrizados (contratante, valor, forma de pagamento, vigência). "
    "Contratada (Smart Data) em texto fixo na primeira cláusula."
)

CLAUSULAS: list[tuple[str, str]] = [
    (
        "Partes",
        """Esse contrato visa documentar a proposta de prestação de serviços, apresentada pela empresa SMART DATA SOLUÇÕES DIGITAIS LTDA., com inscrição no CNPJ sob o nº 33.015.778/0001-23, situado na Rua Desembargador Motta, 1499, Conj. 102, Batel - Curitiba - PR, CEP 80420-164, neste ato representado por seu diretor CARLOS HENRIQUE BOMFIM DE SOUZA, CPF nº 046.860.949-09, neste ato denominada simplesmente de CONTRATADA.

E aceita previamente por {{razao_social}}, com inscrição no CNPJ sob o nº {{cnpj}}, situado na {{endereco}}, neste ato representado por {{responsavel_nome}}, CPF nº {{responsavel_cpf}}, neste ato denominada simplesmente de CONTRATANTE.

Por este ato RESOLVEM, na melhor forma de direito, firmar a presente CONTRATO DE PRESTAÇÃO DE SERVIÇOS, o qual se regerá pelas cláusulas abaixo identificadas.""",
    ),
    (
        "Cláusula primeira — Do objeto",
        """1.1. O presente contrato tem por objeto a licença de uso, implementação, manutenção e personalização do sistema gerencial e painel(is) de Business Intelligence.

O detalhamento complementar pode ser informado abaixo, conforme proposta comercial e registro nos dados cadastrais deste contrato:

{{objeto_contrato}}

Parágrafo Primeiro:

A implementação contempla o desenvolvimento e a personalização conforme as necessidades e prioridades definidas pela CONTRATANTE.

A CONTRATADA realizará uma análise detalhada sobre os processos da CONTRATANTE, visando gerar um desenvolvimento personalizado que atenda de forma precisa às suas demandas específicas.

Parágrafo Segundo:

Durante o período de entrega dos módulos do escopo inicial da proposta comercial, que será concluído em até 90 (noventa) dias, não haverá contabilização de horas adicionais de desenvolvimento.

Após a entrega da primeira versão dos módulos acordados na proposta comercial, que incluem Cadastros e Níveis de Acesso, Gestão de Processos, Leitor de processos e sentença via IA, Módulo de gestão de Contas a Receber e Emissão de Recibos, a CONTRATANTE poderá demandar até 08 (oito) horas de melhorias, ajustes ou novos desenvolvimentos mensais.""",
    ),
    (
        "Cláusula segunda — Da execução dos serviços",
        """2.1. Os trabalhos serão desenvolvidos mediante a aplicação de procedimentos técnicos reconhecidos para a atividade do cliente, abrangendo inclusive análise sumária e avaliação das necessidades do projeto.

Parágrafo Primeiro:

Os serviços serão prestados com total autonomia, liberdade de horário, sem pessoalidade e sem qualquer subordinação ao CONTRATANTE.""",
    ),
    (
        "Cláusula terceira — Observância a sigilo e LGPD",
        """3.1. A CONTRATADA declara que tanto o desenvolvimento da solução quanto o uso desta observarão as disposições da Lei nº 13.709/18 que regulamenta a proteição de dados pessoais e da Lei nº 12.965/14 que regulamenta o Marco Civil da Internet, em especial:

O tratamento de dados pessoais somente poderá ser realizado mediante o fornecimento de consentimento pelo titular ou outra base legal que permita.

O consentimento previsto na frase anterior deverá ser fornecido por escrito ou por outro meio que demonstre a manifestação da vontade do titular.

A não observância de qualquer disposição das referidas leis implicará em responsabilidade exclusiva do infrator.

Parágrafo Primeiro:

A CONTRATADA ainda se obriga a:

1. tratar e usar os dados pessoais nos termos legalmente permitidos, em especial coletando, registrando, organizando, conservando, consultando ou transmitindo os mesmos apenas e somente nos casos em que o seu titular tenha dado o consentimento inequívoco ou na forma legalmente prevista;

2. tratar os dados de modo compatível com as finalidades para os quais tenham sido obtidos;

3. conservar os dados apenas durante o período necessário ao cumprimento das finalidades ou do tratamento posterior, garantindo a sua confidencialidade;

4. implementar as medidas técnicas e organizacionais necessárias para proteger os dados contra a destruição, acidental ou ilícita, a perda acidental, a alteração, a difusão ou o acesso não autorizado, bem como contra qualquer outra forma de tratamento ilícito;

5. informar imediatamente a CONTRATANTE, devendo prestar toda a colaboração necessária a qualquer investigação que venha a ser realizada, caso exista alguma quebra de segurança, ou suspeita da mesma, independentemente de colocar ou não em causa a segurança e integridade dos dados pessoais;

6. garantir o exercício, pelos titulares, dos respectivos direitos de informação, acesso e oposição;

7. assegurar que os respectivos colaboradores, empregados ou os prestadores de serviços externos por si contratados e que venham a ter acesso a dados pessoais no contexto do Contrato cumpram as disposições legais aplicáveis em matéria de proteção de dados pessoais, não cedendo ou divulgando tais dados pessoais a terceiros, nem deles fazendo uso para quaisquer fins que não os estritamente consentidos pelos respectivos titulares.

Parágrafo Segundo:

Para fins deste Contrato, considera-se “dado pessoal” toda informação relacionada à pessoa física identificada ou identificável ou que remeta a sua origem racial ou étnica, convicção religiosa, opinião política, filiação a sindicato ou a organização de caráter religioso, filosófico ou político, dado referente à saúde ou à vida sexual, dado genético ou biométrico.

Parágrafo Terceiro:

“Informações confidenciais” significam os dados confidenciais e/ou as informações desenvolvidas ou adquiridas pela CONTRATADA, e cuja divulgação, por qualquer das partes é vedada taxativamente, a menos que expressamente autorizada pela outra parte.

Parágrafo Quarto:

A CONTRATADA assume expressamente o compromisso de manter em sigilo toda e qualquer informação que venha a ter acesso sobre as operações da empresa em virtude dos trabalhos previstos nesta prestação de serviços, devendo a CONTRATADA proteger as informações confidenciais divulgadas pela Parte reveladora contra o uso ou revelação não autorizada, com o mesmo cuidado e proteção que utilizam para proteger suas próprias informações confidenciais.

Cada Parte obriga-se a utilizar as Informações Confidenciais de forma proba, diligente e razoável, estritamente de acordo com as orientações da Parte reveladora, tão somente para atingir os fins especificamente necessários dentro do âmbito da relação comercial.

Cada uma das PARTES será responsável, isoladamente, por seus agentes, administradores, sócios, parceiros, empregados ou contratados ou quaisquer partes relacionadas, que ocasionarem eventuais vazamentos ou quaisquer outros problemas relacionados ao tratamento de dados pessoais e dados pessoais sensíveis que ocasionar.

A CONTRATADA compromete-se a divulgar as Informações Confidenciais apenas aos seus empregados, colaboradores, administradores, sócios, diretores, partes relacionadas diretamente envolvidos na prestação do serviço. As informações confidenciais serão divulgadas somente naquilo que for estritamente necessário para a realização do serviço, devendo, ainda, assegurar, mediante acordo escrito, que esses Representantes respeitem os termos deste Compromisso, guardando sigilo sobre as Informações Confidenciais e não as divulgando para quaisquer terceiros, respondendo a Parte receptora por todo e qualquer uso e divulgação não autorizados das Informações Confidenciais por seus Representantes.

Ao término da vigência deste contrato, ou a requerimento, por escrito, da outra Parte Reveladora, toda Informação Confidencial que vier a ser disponibilizada à Parte Receptora em razão deste Compromisso, juntamente com todas as suas cópias tangíveis que tenham sido produzidas, todas as anotações, descrições, resumos e materiais envolvendo as Informações Confidenciais ou nelas baseados, deverão ser destruídas ou devolvidas à outra parte, a exclusivo critério desta, no prazo razoável requerido por ela.

Todas as Informações Confidenciais a que as Partes tiverem acesso permanecerão sendo de exclusiva propriedade da outra parte. Cada Parte aceita e concorda que não possui e nem possuirá quaisquer direitos sobre as Informações Confidenciais da Parte contrária, sendo as respectivas Informações Confidenciais de propriedade exclusiva de cada uma das Partes, observada a legislação aplicável. Nenhuma cláusula deste Termo será interpretada como cessão de qualquer direito pertinente às Informações Confidenciais.

Parágrafo Quinto:

O dever de confidencialidade por parte da CONTRATADA previsto nesta cláusula é devido durante a execução do contrato, assim como permanece por 5 (cinco) anos após o encerramento do contrato.

A constatação de qualquer infração a esta Cláusula Terceira sujeitará a parte infratora ao pagamento de indenização pelas perdas e danos a que der causa, sem prejuízo da aplicação de toda e qualquer sanção cível ou penal prevista na legislação brasileira.""",
    ),
    (
        "Cláusula quarta — Da remuneração",
        """4.1. Em contrapartida aos serviços prestados pela CONTRATADA, a CONTRATANTE efetuará o pagamento de R$ {{valor_contrato}} mensais. Os pagamentos iniciarão {{dias_pagamento}} dias corridos após a assinatura do contrato e serão efetuados mediante transferência bancária, PIX ou outro meio de pagamento combinado entre as Partes, em conta a ser indicada pela CONTRATADA.

Parágrafo Primeiro:

O valor estabelecido no caput será reajustado anualmente pelo IPCA acumulado, considerando como data base a data de início deste contrato.

Parágrafo Segundo:

Caso os pagamentos não ocorram no prazo estipulado acima, ocorrerá a aplicação de 2% (dois por cento) de multa sobre o valor da retribuição mensal, mais 1% (um por cento) de juros ao mês, ou fração, calculados pro rata die entre a data do vencimento e a data do efetivo pagamento.

Parágrafo Terceiro:

Caso a CONTRATADA esteja inadimplente com quaisquer de suas obrigações contratuais, a CONTRATANTE a notificará, por escrito, para regularizar a situação em até 7 (sete) dias; após este prazo, caso mantida a irregularidade, a CONTRATANTE poderá, sem que se configure inadimplemento ou violação a este instrumento, suspender os pagamentos à CONTRATADA.""",
    ),
    (
        "Cláusula quinta — Das obrigações da Contratante",
        """5.1. A CONTRATANTE obriga-se a:

1. Cumprir todas as obrigações descritas no presente acordo, bem como agir de modo a dar fiel cumprimento ao pactuado;

2. Dar acesso e disponibilizar as informações, documentos e demais necessidades relevantes ao cumprimento do objeto contratual e/ou em decorrência de exigências legais;

3. Realizar o pagamento da CONTRATADA de acordo com o estipulado na cláusula quarta do presente contrato.""",
    ),
    (
        "Cláusula sexta — Das obrigações da Contratada",
        """6.1. A CONTRATADA obriga-se a:

1. Cumprir todas as obrigações descritas no presente acordo, bem como agir de modo a dar fiel cumprimento ao pactuado;

2. Verificar e solucionar eventuais reclamações e problemas quando do cumprimento do presente objeto contratual;

3. Prestar os serviços contratados de acordo com as especificações e prazos que forem acordados entre as Partes;

4. Quando requerido pela CONTRATANTE, elaborar relatórios acerca do andamento dos serviços que estão sendo prestados.

Parágrafo único:

A CONTRATADA se responsabiliza:

1. Pela correta utilização técnica dos softwares e ferramentas eventualmente disponibilizados pela CONTRATANTE, sob pena de responder por eventuais perdas e danos causados pela má utilização;

2. Pela prestação dos serviços contratados, seguindo as orientações e requerimentos da CONTRATANTE.""",
    ),
    (
        "Cláusula sétima — Do prazo de entrega",
        """7.1. Fica estipulado à CONTRATADA o prazo de {{prazo_conclusao}} para a entrega e conclusão da primeira versão funcional da aplicação conforme descrição na Cláusula Primeira (Objeto), ao CONTRATANTE, a contar a partir da reunião de briefing e alinhamento a ser acordada entre as partes.""",
    ),
    (
        "Cláusula oitava — Prazo de vigência",
        """8.1. O presente contrato vigorará a partir de {{data_inicio}}, por prazo indeterminado, todavia permanecerá condicionado à assinatura deste instrumento e à resolução mediante o fiel cumprimento das obrigações aqui assumidas por ambas as partes.""",
    ),
    (
        "Cláusula nona — Rescisão, desistência ou cancelamento",
        """9.1. O presente contrato poderá ser rescindido por qualquer uma das PARTES sem quaisquer ônus, mediante notificação escrita à parte contrária com antecedência mínima de {{dias_antecedencia_rescisao}} dias.

9.2. O presente contrato poderá ser alterado consensualmente pelas Partes, por meio de termo aditivo, que deverá ser anexado ao presente.

9.3. Quaisquer leis, decretos, portarias, tributos, impostos, contribuições, convenções ou encargos legais aplicáveis ao Contrato, que forem criados, alterados ou extintos após a data base contratual, que venham impactar no preço da prestação de serviços ou provocar o desequilíbrio econômico-financeiro do contrato, deverão ser considerados pelas Partes, promovendo-se os ajustes necessários nos parâmetros e condições contratuais diretamente afetados, de forma a serem considerados nos faturamentos correspondentes, tão logo vigorarem.

9.4. O presente contrato poderá ser rescindido, a qualquer momento, caso alguma das Partes não cumpra as obrigações descritas, resguardando-se o direito a receber, de maneira proporcional, a contraprestação pelos serviços prestados, bem como qualquer tipo de indenização pelo não cumprimento do acordado.

9.5. O presente contrato poderá ser rescindido de imediato, independentemente de qualquer notificação judicial ou extrajudicial, nas seguintes hipóteses:

• Falência, recuperação judicial ou dissolução de qualquer uma das Partes; e

• Quando da utilização de mão de obra infantil ou trabalho irregular de adolescentes.

9.6. A CONTRATANTE pode reduzir o plano a qualquer momento, mediante aviso prévio com antecedência de {{dias_antecedencia_rescisao}} dias. A redução de horas e valores deverá ser acordada com a CONTRATADA, respeitando a política comercial vigente no momento da solicitação.

9.7. Caso a CONTRATANTE decida não contratar mais horas de melhorias mensais, é necessário informar a CONTRATADA com {{dias_antecedencia_rescisao}} dias de antecedência. Nesse caso, apenas o valor de manutenção de R$ {{valor_manutencao}} será cobrado, o qual contempla hospedagem, licenças, manutenção e backup.""",
    ),
    (
        "Cláusula décima — Das disposições gerais",
        """10.1. A CONTRATANTE não possui qualquer gerência sobre o local e horário da prestação dos serviços prestados pela CONTRATADA, sendo esta livre para a escolha do melhor horário e local para a realização do serviço, desde que cumpridas as tarefas e prazos estipulados entre as Partes. Não há, portanto, entre a CONTRATANTE e a CONTRATADA qualquer tipo de relação de subordinação.

10.2. A prestação dos serviços descritos na Cláusula Primeira não constitui qualquer vínculo de natureza empregatícia, inexistindo qualquer responsabilidade da CONTRATANTE neste sentido. Da mesma forma, a prestação de tais serviços não geram qualquer vínculo societário entre as Partes.

10.3. As comunicações relevantes para a execução do presente contrato, como prazos e especificações, deverão ser realizadas por escrito, por meio de e-mail ou outro tipo de mensagem eletrônica combinada entre as Partes.

10.4. As Partes concordam que o descumprimento de qualquer obrigação que seja tolerado, sem exercício da respectiva multa pela Parte contrária, será entendido como mera liberalidade ou tolerância, não constituindo precedente, novação ou alteração do que fora pactuado neste contrato, permanecendo, assim, em vigor, íntegras e exigíveis todas as suas cláusulas e condições.

10.5. É vedado à CONTRATADA transferir, total ou parcialmente, este contrato a terceiros, sem a prévia autorização, por escrito, da CONTRATANTE.

10.6. O presente contrato prevalece e revoga qualquer outro contrato ou acordo, verbal ou escrito, estipulado entre as Partes, em data anterior à assinatura deste instrumento, que sejam conflitantes com as disposições previstas neste contrato.""",
    ),
    (
        "Cláusula décima primeira — Do foro e encerramento",
        """11.1. As Partes elegem o foro da Comarca de Curitiba, Estado do Paraná, para dirimir quaisquer controvérsias oriundas deste contrato, renunciando a qualquer outro, por mais privilegiado que seja.

As Partes assim justos e contratantes assinam o presente instrumento em duas vias de igual teor e forma.

Curitiba, {{data_inicio}}.

Espelhos de assinatura (assinaturas manuscritas nas vias físicas quando aplicável):

Contratada — SMART DATA SOLUÇÕES DIGITAIS LTDA. — CNPJ 33.015.778/0001-23 — Representante: Carlos H. Bomfim de Souza

Contratante — {{razao_social}} — CNPJ {{cnpj}} — Representante: {{responsavel_nome}} — CPF {{responsavel_cpf}}""",
    ),
]


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    empresa = sa.table("empresa", sa.column("empId", sa.Integer))
    existe_empresa = conn.execute(sa.select(sa.func.count()).select_from(empresa)).scalar() or 0
    if existe_empresa == 0:
        return

    ver = conn.execute(
        sa.text("SELECT COUNT(*) FROM empresa WHERE empId = :e").bindparams(sa.bindparam("e", EMP_ID))
    ).scalar()
    if (ver or 0) == 0:
        return

    existe = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM contrato_modelo WHERE ctmEmpId = :emp AND ctmNome = :nome"
        ).bindparams(sa.bindparam("emp", EMP_ID), sa.bindparam("nome", MODELO_NOME))
    ).scalar()
    if (existe or 0) > 0:
        return

    cm = sa.table(
        "contrato_modelo",
        sa.column("ctmEmpId", sa.Integer),
        sa.column("ctmNome", sa.String),
        sa.column("ctmDescricao", sa.Text),
        sa.column("ctmAtivo", sa.Boolean),
        sa.column("ctmDataCriacao", sa.DateTime(timezone=True)),
        sa.column("ctmDataAtualizacao", sa.DateTime(timezone=True)),
    )
    insert_res = conn.execute(
        sa.insert(cm).values(
            ctmEmpId=EMP_ID,
            ctmNome=MODELO_NOME,
            ctmDescricao=MODELO_DESC,
            ctmAtivo=True,
            ctmDataCriacao=now,
            ctmDataAtualizacao=None,
        )
    )
    pk = insert_res.inserted_primary_key
    if pk is not None and len(pk):
        ctm_id = pk[0]
    else:
        ctm_id = conn.execute(sa.text("SELECT LAST_INSERT_ID()")).scalar()
    assert ctm_id is not None

    cmc = sa.table(
        "contrato_modelo_clausula",
        sa.column("cmcEmpId", sa.Integer),
        sa.column("cmcCtmId", sa.Integer),
        sa.column("cmcTitulo", sa.String),
        sa.column("cmcTextoPadrao", sa.Text),
        sa.column("cmcUtilizarPadrao", sa.Boolean),
        sa.column("cmcOrdem", sa.Integer),
        sa.column("cmcAtivo", sa.Boolean),
        sa.column("cmcDataCriacao", sa.DateTime(timezone=True)),
        sa.column("cmcDataAtualizacao", sa.DateTime(timezone=True)),
    )

    for ordem, (titulo, texto) in enumerate(CLAUSULAS, start=1):
        conn.execute(
            cmc.insert().values(
                cmcEmpId=EMP_ID,
                cmcCtmId=ctm_id,
                cmcTitulo=titulo[:200],
                cmcTextoPadrao=texto,
                cmcUtilizarPadrao=True,
                cmcOrdem=ordem,
                cmcAtivo=True,
                cmcDataCriacao=now,
                cmcDataAtualizacao=None,
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """DELETE FROM contrato_modelo_clausula WHERE cmcCtmId IN (
            SELECT ctmId FROM contrato_modelo WHERE ctmEmpId = :emp AND ctmNome = :nome
        )"""
        ).bindparams(sa.bindparam("emp", EMP_ID), sa.bindparam("nome", MODELO_NOME))
    )
    conn.execute(
        sa.text("DELETE FROM contrato_modelo WHERE ctmEmpId = :emp AND ctmNome = :nome").bindparams(
            sa.bindparam("emp", EMP_ID), sa.bindparam("nome", MODELO_NOME)
        )
    )
