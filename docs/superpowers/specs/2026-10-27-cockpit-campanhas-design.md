# Cockpit de Campanhas — Especificação de design

- **Data:** 27/10/2026
- **Autor:** Carlos Souza (com Claude)
- **Status:** implementada (migrations 0037–0039 pendentes de aplicação)
- **Base:** monitoramento de campanhas Meta já entregue (`2026-10-26-monitoramento-campanhas-meta-design.md`):
  dados por anúncio, funil lead → MQL → oportunidade → contrato, resumo diário com IA, alertas e
  ferramentas MCP. Protótipo validado pelo Carlos em 27/10/2026:
  https://claude.ai/artifact/1UTtsohaiujPABL2t9cHCe

## 1. Intenção

A página Campanhas hoje é uma tabela de 21 colunas: completa, mas só quem já é gestor de tráfego
sabe o que fazer com ela. O Carlos quer transformá-la num **cockpit de decisão**: a tela deve
mostrar como um gestor de tráfego avalia as campanhas, de forma visual o bastante para **um leigo
entender o resultado** e saber o que fazer, com um **agente de IA** que interpreta os números e
responde perguntas.

O raciocínio que a tela segue é o de um gestor de tráfego:

1. **Veredito** — está bom, em atenção ou ruim, e por quê, em uma frase.
2. **Custo por etapa** — quanto custa cada lead, cada MQL, cada oportunidade, comparado com a meta.
3. **Onde o funil perde mais** — a etapa que é o gargalo agora.
4. **Tendência** — está melhorando ou piorando mês a mês.
5. **Decisão por criativo** — escalar, otimizar custo, rever público ou pausar.
6. **Saúde da operação** — o dado é confiável (rastreio) e o time está atendendo (1º contato).

Com os dados de hoje (01/06 a 26/10), a leitura esperada é: o custo por lead caiu de R$ 305 em
agosto para R$ 120 em outubro, mas só 3 de 36 leads viraram MQL. O gargalo é a qualidade do lead,
não o custo, e nenhum criativo está no quadrante "Escalar".

### Critérios de sucesso

1. Uma pessoa que não é da área abre a tela e diz, sem ajuda, se as campanhas estão indo bem, qual
   é o maior problema e o que fazer com cada criativo.
2. Todos os números do cockpit batem com a tabela detalhada da mesma tela (e, por ela, com o
   Gerenciador de Anúncios, como já conferido nas fases anteriores).
3. A leitura da IA e as respostas do analista usam só os números mostrados na tela e nunca trazem
   dados pessoais de lead.

## 2. Decisões tomadas (pelo Carlos)

| Decisão | Escolha |
|---|---|
| Visual | Padrão visual atual do CRM (não o design system Smart Data). |
| Estrutura da tela | A do protótipo aprovado, nesta ordem: filtros → leitura do analista (IA) com "Pergunte ao analista" → 8 indicadores → funil "Do anúncio ao contrato" → gráficos mensais → matriz de decisão dos criativos → tabela "o que fazer com cada criativo" → saúde da operação. |
| IA | Interpreta os resultados (leitura do período) e responde perguntas sobre eles. |
| Metas | Configuráveis; ponto de partida CPL R$ 150 e 10% dos leads virando MQL (os valores do protótipo). |
| Definições do funil | As do monitoramento: MQL = chegou a "Reunião de Levantamento"; oportunidade = qualquer estágio a partir de "Reunião de Vendas"; contrato = ganho. |

## 3. Objetivos, não objetivos e anti-objetivos

**Objetivos:** a página Campanhas vira o cockpit do protótipo; metas de CPL e de taxa de MQL na
configuração do monitoramento; classificação de cada criativo num quadrante de decisão; selo de
saúde por indicador e para o período; leitura do período por IA; "Pergunte ao analista" com
perguntas livres sobre os números do período; uma ferramenta MCP com os mesmos dados do cockpit.

**Não objetivos (fica para depois):** qualquer ação na conta da Meta (pausar, orçamento, criar);
visão por público, posicionamento ou dispositivo; Google Ads; histórico das conversas com o
analista; leitura gerada automaticamente sem alguém pedir; mudanças na tela Monitoramento e na
faixa do Dashboard.

**Anti-objetivos (seria fracasso mesmo funcionando):**
- uma recomendação forte ("Pausar", "Escalar") apoiada em 1 ou 2 leads sem avisar que a amostra é
  pequena;
- números do cockpit que divergem da tabela detalhada da mesma tela;
- a IA inventar número, comparar com "média do mercado" que não recebeu, ou sugerir que ela mesma
  vai mexer na conta;
- nome, telefone ou e-mail de lead na leitura, no chat, na resposta do MCP ou no que é enviado à IA;
- a tela abrir mais lenta que hoje porque espera a IA.

## 4. Situação atual relevante

- `frontend/src/pages/Campanhas/CampanhasPage.tsx`: filtros (De/Até, Mês atual, Ano atual, Conta,
  Só campanhas ativas), 10 cartões, tabela em árvore campanha → conjunto → anúncio, lista de
  revisão de origem e modal de detalhe da campanha. Período padrão: ano corrente.
- `GET /meta-ads/painel` (`services/meta_ads/indicadores.py::painel`) devolve total, árvore,
  "não identificada", cobertura e revisão de origem. Cada linha (`MetaAdsLinha`) já tem
  investimento, impressões, cliques, leads Meta e CRM, MQLs, oportunidades, contratos, MRR,
  projeto, CTR, CPC, CPL, custos por etapa, CAC, retorno e horas até o 1º contato.
- Contagem do funil por evento no período (`funil.contar`): cada etapa conta pela própria data.
  Por isso uma taxa de passagem pode passar de 100% num período curto.
- Configuração do monitoramento (`meta_ads_monitor_config`, uma linha por empresa) com estágios de
  MQL/oportunidade, limites dos alertas (`mmcCplFator` etc.) e hora do resumo, editada em
  `ConfigMonitoramentoModal.tsx`.
- IA: `services/llm/llm_factory.get_scope_provider()` com `chat_completion(messages, temperature)`,
  já usado pela leitura do resumo diário (`services/meta_ads/resumo.py::gerar_leitura`), que falha
  de forma controlada (sem chave → resumo sem leitura e com aviso).
- MCP: `resumo_campanhas`, `funil_por_criativo`, `alertas_campanhas`, `resumo_diario`
  (`mcp_crm/ferramentas/campanhas.py`).
- Frontend sem biblioteca de gráficos (dependências: react, react-dom, react-router-dom, axios).
- Última migration: `0036_meta_ads_resumo`.

## 5. O que será construído

### 5.1 Metas na configuração do monitoramento

Dois campos novos em `meta_ads_monitor_config`, editáveis no modal de configuração (seção "Metas do
cockpit"), só admin, como os demais:

| Campo | Padrão | Uso |
|---|---|---|
| Meta de CPL (R$) | 150,00 | linha vertical da matriz; selo do CPL |
| Meta de taxa de MQL (%) | 10 | linha horizontal da matriz; selo dos MQLs |

A **meta implícita de custo por MQL** = meta de CPL ÷ (meta de taxa ÷ 100) (R$ 1.500 com os
padrões), mostrada no cartão de custo por MQL. Validação: CPL > 0; taxa entre 0,1 e 100.

### 5.2 Período e comparação

- Atalhos: **Últimos 30 dias**, **Mês atual**, **Ano atual** e **Personalizado** (De/Até, como
  hoje). O padrão continua o **ano corrente**.
- "Ano atual" e "Mês atual" vão do primeiro dia até hoje; "Últimos 30 dias" = hoje e os 29 dias
  anteriores.
- Filtros mantidos: Conta e Só campanhas ativas. Valem para tudo no cockpit (menos os alertas
  abertos, ver 5.9).
- **Comparar com período anterior** (ligado por padrão): mesmo número de dias, imediatamente antes
  do início, com os mesmos filtros e as mesmas regras do painel. Os cartões mostram a variação.
  Desligado, os cartões mostram a tendência do período no lugar (ver 5.4). Quando o período
  anterior não tem investimento nem lead (é o caso do ano corrente, porque os dados começam em
  junho), a linha do cartão diz "sem dados no período anterior" e mostra a tendência.

### 5.3 Selo de saúde

Quatro selos, sempre com o texto escrito (nunca só a cor): **Bom**, **Atenção**, **Ruim** e
**Sem dados**.

| Indicador | Bom | Atenção | Ruim | Sem dados |
|---|---|---|---|---|
| CPL | ≤ meta | ≤ meta × `mmcCplFator` | acima disso | sem lead da Meta |
| Taxa de MQL (MQLs ÷ leads CRM) | ≥ meta | ≥ 60% da meta | abaixo disso | sem lead no CRM |
| Custo por MQL | ≤ meta implícita | ≤ meta implícita × `mmcCplFator` | acima disso | sem MQL |

**Saúde do período** (selo da leitura do analista) = o pior entre CPL e taxa de MQL; "Sem dados"
quando não houver lead da Meta. Os demais cartões (investimento, leads, oportunidades, contratos,
retorno) não têm meta e mostram "Sem dados" no lugar do selo, ou nenhum selo (escolha de layout).

### 5.4 Indicadores (8 cartões)

Cada cartão tem: rótulo, valor, selo, uma linha de tendência ou variação e uma frase curta do que o
número significa, para leigo. Os rótulos e frases do protótipo valem como texto de partida.

| Cartão | Valor | Linha de tendência (comparação desligada) |
|---|---|---|
| Investimento | total investido | valor por mês (ou semana) do período |
| Leads | leads da Meta | quantos chegaram ao CRM com o anúncio |
| Custo por lead (CPL) | investimento ÷ leads da Meta | CPL do primeiro e do último mês/semana com gasto |
| MQLs | MQLs | taxa de MQL |
| Custo por MQL | investimento ÷ MQLs | meta implícita |
| Oportunidades | oportunidades | quantos MQLs avançaram |
| Contratos | contratos | — |
| Retorno | (MRR × 12 + projeto) ÷ investimento | "aparece com o 1º contrato" quando não houver |

Com a comparação ligada, a linha mostra a variação contra o período anterior (ex.: "↓ 61% vs.
período anterior"). Para custos, cair é bom; o texto deixa isso claro ("caiu", "subiu"), sem
depender só de seta ou cor.

### 5.5 Funil "Do anúncio ao contrato"

Sete degraus: viram o anúncio (impressões) → clicaram → viraram lead (leads Meta) → chegaram ao
CRM → viraram MQL → oportunidade → contrato. Cada degrau mostra a quantidade, a taxa de passagem do
degrau anterior em linguagem simples ("1,39% de quem viu") e o custo de chegar até ali (CPM, CPC,
CPL, custo por lead do CRM, custo por MQL, custo por oportunidade, CAC).

- As barras **não são proporcionais** (155 mil impressões contra 3 MQLs deixaria o fim invisível):
  larguras decrescentes fixas, com o número escrito em cada uma.
- **Gargalo:** entre as passagens a partir de "chegaram ao CRM" (CRM → MQL, MQL → oportunidade,
  oportunidade → contrato), a de menor taxa, considerando só passagens cuja etapa de origem tem pelo
  menos 3 entradas no período. O degrau ganha o destaque "maior perda" e uma frase como "Para cada
  12 leads, só 1 chega à reunião de levantamento". Sem passagem elegível, sem destaque.
- Taxa acima de 100% (possível pela contagem por evento) aparece como calculada, com a dica
  "contagem por evento no período: inclui leads que entraram antes".

### 5.6 Gráficos de tendência

Dois gráficos, lado a lado em tela larga e empilhados em tela estreita:

1. **Investimento e custo por lead:** barras de investimento e linha do CPL por intervalo.
2. **Leads: Meta x CRM:** barras agrupadas por intervalo.

Intervalo: **mês** quando o período tem mais de 62 dias; senão **semana** (segunda a domingo,
cortada nas pontas do período).

**A série soma exatamente o total do cockpit.** Ela usa as mesmas campanhas incluídas no total
(filtros de conta e de ativas, mais os leads sem campanha) e a mesma contagem por evento. Como cada
evento tem uma única data, as contagens de intervalos que não se sobrepõem somam o total. O gasto
vem do insight de campanha, como no total. Os leads do funil são carregados uma vez só e contados
por intervalo; o painel não é chamado uma vez por intervalo. Intervalos sem gasto e sem lead nas pontas do período ficam de fora
(o ano corrente começa no primeiro mês com movimento); no meio, aparecem zerados. Cada ponto mostra o
valor ao passar o mouse ou focar pelo teclado, e cada gráfico tem descrição acessível com os
valores.

### 5.7 Matriz de decisão dos criativos

Um ponto por **anúncio com investimento no período**. Eixo horizontal: CPL (mais à direita = mais
caro). Eixo vertical: taxa de MQL (mais acima = mais leads viram MQL). Tamanho: investimento. Linhas
tracejadas nas metas de 5.1. Quadrantes e recomendação:

| Quadrante | Regra | Recomendação |
|---|---|---|
| Escalar | CPL ≤ meta **e** taxa ≥ meta | lead barato e que vira reunião: candidato a receber mais verba |
| Otimizar custo | CPL > meta **e** taxa ≥ meta | traz MQL, mas cada lead está acima da meta: testar público ou lance |
| Rever público | CPL ≤ meta **e** taxa < meta | lead barato que ainda não vira reunião: rever público e perguntas do formulário |
| Pausar | CPL > meta **e** taxa < meta | caro e sem qualificação: candidato a pausar |

- Anúncio com gasto e **sem lead da Meta** não tem CPL: vai para "Pausar" se o gasto no período
  for ≥ `mmcGastoSemLead`; abaixo disso fica como **"Aguardar dados"**, sem quadrante. Na matriz,
  esses anúncios aparecem numa faixa à direita "sem lead".
- Anúncio **com lead da Meta e nenhum lead no CRM** ligado a ele não tem taxa de MQL (0 ÷ 0): fica
  como "Aguardar dados", com o motivo "os leads ainda não chegaram ao CRM com este anúncio" (é uma
  falha de rastreio, não um criativo ruim). Fica fora da matriz e aparece na tabela.
- Entram **todos os anúncios com gasto no período**, ativos ou não. A tabela mostra o status; para
  um anúncio que já não está ativo, a recomendação vem com o complemento "(já pausado)", e
  "Pausar" vira "Manter pausado".
- A taxa de MQL acima de 100% (contagem por evento) é usada como calculada no quadrante; na matriz,
  o ponto fica no topo do eixo, que vai de 0 até o maior entre o dobro da meta e a maior taxa,
  limitado a 100%.
- **Amostra pequena:** anúncio com menos de **5 leads no CRM** recebe a marca "amostra pequena" no
  ponto e na tabela; a recomendação continua, mas com o aviso. Assim o anti-objetivo de recomendar
  forte com 1 lead fica coberto sem esconder o criativo.
- A taxa de MQL do anúncio usa os leads do CRM ligados àquele anúncio (mesma regra da árvore em
  `indicadores.painel`).
- Rótulos dos pontos: nome curto do anúncio; o nome completo vai na dica e na tabela.

### 5.8 Tabela "o que fazer com cada criativo"

Uma linha por anúncio da matriz (e os "Aguardar dados"), com: criativo, campanha, investido, leads,
CPL, MQLs, taxa de MQL, recomendação (etiqueta com texto) e "por quê" (uma frase da regra, como no
protótipo, mais "amostra pequena" quando houver). Ordenada pelo investimento, do maior para o
menor.

### 5.9 Saúde da operação

Quatro cartões:

- **Rastreio dos leads:** cobertura do painel (meta 90%).
- **Tempo até o 1º contato:** média de horas do total do painel (`horasPrimeiroContato`).
- **Alertas abertos:** quantidade de alertas com status "aberto" da empresa (a mesma contagem do
  resumo diário, sem filtro de conta ou período), com link para a tela Monitoramento.
- **Origem a revisar:** quantidade de leads da revisão de origem, com link para a lista na mesma
  página. O cockpit mostra só a contagem; a lista com nomes continua onde está hoje.

### 5.10 Tabela detalhada

A tabela em árvore atual, a lista de revisão de origem e o modal de detalhe da campanha continuam,
abaixo do cockpit, sob o título "Detalhe por campanha". Os 10 cartões atuais saem (os 8 novos e a
saúde da operação os substituem; o CAC continua na tabela).

### 5.11 Leitura do analista (IA)

- Cartão no topo, com o **selo de saúde do período** (5.3, por regra, sem IA) e a **frase do
  gargalo** (5.5, por regra) sempre visíveis, mesmo sem IA.
- Botão **"Gerar leitura"**: a IA devolve uma **manchete** (uma frase com o veredito e o porquê) e
  três blocos curtos: **o que funciona**, **onde está o problema**, **o que olhar agora**. A tela
  abre sem esperar a IA.
- A leitura é **guardada**: uma por recorte (empresa, datas de início e fim já resolvidas, conta e
  filtro de ativas), e gerar de novo substitui a anterior. Junto vão a data/hora em que foi gerada
  e uma impressão digital do contexto enviado à IA, metas incluídas. A opção "Comparar" não faz
  parte do recorte, porque a IA sempre recebe o período anterior. Ao abrir o mesmo recorte com o
  mesmo contexto, a leitura guardada aparece direto. Se o contexto mudou (números ou metas),
  aparece a leitura antiga marcada "gerada com números anteriores" e o botão vira "Gerar de novo".
  Atalhos relativos ("Últimos 30 dias") mudam de datas a cada dia e pedem leitura nova, o que é
  esperado, porque os números também mudam.
- O que vai para a IA: totais do período e do período anterior, a série por intervalo, o funil com
  taxas e gargalo, as metas, e os criativos com nome, campanha, números e quadrante (até os 30 de
  maior investimento). Nunca `revisaoOrigem`, nomes, telefones ou e-mails de lead.
- Regras do prompt: usar só os números recebidos; dizer quando a amostra é pequena; não citar
  referência externa; recomendar o que verificar ou testar, nunca dizer que vai agir na conta;
  português simples, para quem não é da área.
- Sem IA configurada ou em erro: o cartão mostra o selo, o gargalo e o aviso "Leitura por IA
  indisponível", como no resumo diário.

### 5.12 Pergunte ao analista

- Painel ao lado da leitura: três perguntas sugeridas ("Qual criativo devo escalar?", "Por que o
  custo por lead mudou?", "Onde perco mais leads no funil?") e um campo livre.
- Cada pergunta vai ao servidor com o recorte atual; o servidor sempre remonta **o mesmo contexto da
  leitura (5.11)** a partir do banco e responde em texto curto. A conversa vale só enquanto a tela
  está aberta e nada é guardado.
- Para dar continuidade, o cliente manda as até 6 últimas trocas. O servidor aceita só os papéis
  pergunta e resposta, com até 2.000 caracteres cada; o resto é descartado. As instruções e o
  contexto dos números vêm sempre do servidor, nunca do cliente.
- Pergunta com até 500 caracteres. Mesmas regras de prompt da leitura, mais: se a pergunta não
  puder ser respondida com esses números, dizer isso e sugerir o que olhar.
- Limite de **30 perguntas por usuário por dia** (America/Sao_Paulo); ao passar, a tela avisa
  "limite de perguntas de hoje atingido". A contagem é guardada por usuário e dia.
- Disponível para quem acessa a página Campanhas (não só admin). Sem IA configurada, o painel
  mostra o aviso e não envia.

### 5.13 Ferramenta MCP

Nova ferramenta de leitura `cockpit_campanhas(data_inicial, data_final)`: totais e período
anterior, saúde, funil com gargalo, série e criativos com quadrante e marca de amostra pequena.
Mesmos dados que vão para a IA; sem dados pessoais. As ferramentas atuais não mudam.

## 6. Restrições

- As mesmas das fases anteriores: isolamento por empresa em toda consulta; configuração só para
  admin; mensagens em português; SQLite em memória nos testes que precisam de SQL; **migration só
  roda com ok do Carlos** (o banco do `.env` é o real).
- Nenhuma escrita na Meta.
- Nenhum dado pessoal de lead no que vai para a IA, na leitura, no chat e no MCP.
- Os números do cockpit saem da mesma função do painel (`indicadores.painel`) e das mesmas regras
  de funil: nenhuma regra de contagem nova.
- Sem dependência nova no frontend sem necessidade (ver seção 7).
- Acessível: contraste mínimo 4,5:1; selo e recomendação sempre com texto; gráficos com descrição;
  controles alcançáveis pelo teclado; funciona em tela estreita (os blocos empilham).

## 7. Deixado para quem implementa

- Forma da API: um endpoint novo do cockpit ou extensão do painel; nomes de schemas e de campos.
- Nome e forma da tabela que guarda a leitura e da impressão digital dos números.
- Gráficos em SVG feito à mão ou uma biblioteca leve (a escolha precisa caber no padrão do projeto;
  SVG à mão é o caminho preferido, já que o projeto não tem nenhuma).
- Nomes de componentes e arquivos do frontend (sugestão: componentes do cockpit numa pasta própria
  dentro de `pages/Campanhas/`).
- Texto final dos prompts e o formato de saída estruturada da leitura (JSON com os quatro campos,
  com fallback para texto se a IA não devolver JSON válido).
- Como a matriz trata pontos sobrepostos.

## 8. Decisões que tomei (Claude) e que o Carlos pode trocar

1. A página **Campanhas** vira o cockpit; a tabela detalhada fica embaixo (em vez de criar uma tela
   nova).
2. Período padrão continua o **ano corrente**.
3. Selo "Atenção" do CPL e do custo por MQL usa o mesmo fator do alerta de CPL (`mmcCplFator`,
   1,5×); "Atenção" da taxa de MQL a partir de 60% da meta.
4. Saúde do período = o pior entre CPL e taxa de MQL.
5. Gargalo só a partir de "chegaram ao CRM" e com pelo menos 3 entradas na etapa de origem.
6. Amostra pequena = menos de 5 leads no CRM no anúncio.
7. Anúncio sem lead vai para "Pausar" só a partir do gasto do alerta "gasto sem lead" (R$ 150);
   abaixo disso, "Aguardar dados".
8. Intervalo mensal acima de 62 dias; senão semanal.
9. Leitura da IA só quando alguém pede, guardada por recorte; o chat não guarda histórico.
10. Contexto da IA limitado aos 30 criativos de maior investimento.
11. Chat aberto a todo usuário que vê a página Campanhas, com limite de 30 perguntas por usuário
    por dia.
12. Anúncio com lead na Meta e nenhum no CRM fica em "Aguardar dados" (falha de rastreio), fora da
    matriz.
13. A matriz inclui anúncios já pausados, com "(já pausado)" e "Manter pausado".
14. Metas valem para a empresa toda (não por conta) e entram na impressão digital da leitura.
15. Sem período anterior com dados, o cartão mostra a tendência e avisa.

## 9. Ajustes na implementação

1. Anúncio sem lead da Meta mas com lead no CRM usa os leads do CRM no CPL (a tabela mostra
   "N (CRM)"), para um criativo com MQL não sair como "Pausar".
2. A matriz e a tabela listam só anúncios com investimento no período.
3. "(já pausado)" vale para todos os quadrantes de anúncio inativo, menos "Aguardar dados".
4. O gargalo só aparece quando há perda (taxa abaixo de 100%).
5. Selos e quadrantes comparam a taxa de MQL arredondada em 2 casas, a mesma mostrada na tela.
6. A rota do cockpit exige as duas datas; "todas as contas" é guardado como conta 0 no recorte da
   leitura.
7. Pendente para depois: requisições simultâneas de leitura ou de pergunta podem dar erro 500 em
   vez de esperar; datas invertidas no período personalizado não são recusadas.
