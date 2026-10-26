# Monitoramento de Campanhas Meta no CRM — Especificação de design

- **Data:** 26/10/2026
- **Autor:** Carlos Souza (com Claude)
- **Status:** aguardando revisão
- **Base:** especificação funcional "Agente de Monitoramento de Campanhas Meta" (26/10/2026) e a fase 1
  já entregue (`2026-10-14-meta-ads-campanhas-design.md`: contas, sync diária por campanha, página
  Campanhas, faixa no Dashboard).

## 1. Intenção

A Smart Data quer acompanhar todo dia quanto **cada criativo (anúncio)** custa até virar MQL,
oportunidade e contrato — não só até virar lead — e ser avisada quando algo sai do padrão. Hoje o
acompanhamento é manual no Gerenciador de Anúncios e para no CPL. Esta fase transforma o que a fase 1
já mostra por campanha num monitoramento por anúncio, com resumo diário, alertas e funil, tudo dentro
do CRM. É a base para a fase seguinte (sugestão e geração de criativos), que vai usar o que este
monitoramento mostrar que performa.

### Critérios de sucesso (do documento funcional)

1. O Pedro usa o resumo por duas semanas seguidas e considera que ele substitui a olhada manual no
   Gerenciador de Anúncios.
2. Gasto, leads e CPL do resumo batem com o Gerenciador para o mesmo período. (Gasto, impressões,
   cliques, CTR e CPC por campanha já foram conferidos e batem na fase 1.)
3. Pelo menos 90% dos leads da Meta no período chegam ao CRM com o ID do anúncio.
4. Cada regra de alerta foi testada com um caso real ou simulado e disparou corretamente.
5. O funil por criativo mostra lead, MQL, oportunidade e contrato para todos os anúncios ativos no mês.
6. O token não permite nenhuma escrita na conta (testado).

## 2. Decisões tomadas (pelo Carlos)

| Decisão | Escolha |
|---|---|
| Integração com a Meta | Continua a do CRM (fase 1). **Não** se mistura com a da Adverse; a questão em aberto "como o CRM lê a Adverse" deixa de existir. |
| Acesso | Token de usuário do sistema do Business Manager, só leitura, já testado e funcionando. |
| MQL | Lead que chega ao estágio **"Reunião de Levantamento"** do funil (ou além). |
| Oportunidade | Lead que chega a **qualquer estágio a partir de "Reunião de Vendas"**. |
| Contrato | Lead **ganho** (ou marcado como ganho), com data e valor de fechamento. |
| Formulário nativo | Os leads vêm do formulário nativo da Meta **pela planilha** "Codeseller leads face" (exportação da própria Meta) lida pelo n8n. **Não** haverá integração direta com a Meta (webhook `leadgen`). |
| Origem do lead | O fluxo n8n passa a enviar os IDs de campanha, conjunto e anúncio ao CRM. |
| Leads "Anúncios" sem registro na Meta | Depois da carga retroativa, leads com origem "Anúncios" que não aparecem na planilha da Meta **não contam como Meta**: saem de CPL, vendas e retorno e aparecem numa lista para revisão da origem. |
| Canal do resumo e dos alertas | **Só no CRM** nesta fase (nada de WhatsApp). |
| Escopo | Só leitura na Meta; só Meta (sem Google); sem geração de criativos. |

## 3. Objetivos, não objetivos e anti-objetivos

**Objetivos:** dados por anúncio e por conjunto; rastreio do anúncio em cada lead; funil por
criativo com custo por etapa; resumo diário com leitura; seis alertas configuráveis; perguntas sob
demanda pelo MCP; garantia de token só leitura.

**Não objetivos (fica para depois):** webhook de Lead Ads; envio por WhatsApp ou e-mail; chat dentro
do CRM; qualquer escrita na Meta (criar, pausar, orçamento); geração de criativos; Google Ads;
feriados no cálculo de dia útil.

**Anti-objetivos (seria fracasso mesmo funcionando):**
- números do resumo que não batem com o Gerenciador de Anúncios;
- alertas que disparam todo dia pelo mesmo motivo (ruído faz o time parar de olhar);
- nome, telefone ou e-mail de lead em resumo, análise ou resposta do MCP (só no alerta "lead sem
  contato" e na lista de revisão de origem);
- contar como Meta lead que não veio da Meta (infla o CPL "bom" e o retorno).

## 4. Situação atual relevante

- **Fase 1 em produção:** `meta_ads_conta`, `meta_ads_campanha`, `meta_ads_insight_diario`
  (campanha × dia), sync diária às 4h (30 dias; carga inicial 90), página Campanhas, faixa no
  Dashboard, vínculo lead → campanha por nome/id nos campos UTM (`opoMcgId`).
- **Fluxo n8n "lead Recebido -> CRM -> Whats Pedro"** (id `KbNb0JM8wdQo4jLb`): gatilho de linha nova
  na planilha "Codeseller leads face" (a cada minuto) → **INSERT direto** na tabela `oportunidade`
  (empresa 2, estágio 9 "Contatos", origem 30 "Anúncios", responsável 3; só título, contato, telefone
  e datas) → WhatsApp para o Pedro via uazapi. A planilha traz, por lead: `id` (`l:...`),
  `created_time`, `ad_id` (`ag:...`), `ad_name`, `adset_id` (`as:...`), `adset_name`, `campaign_id`
  (`c:...`), `campaign_name`, `form_id`, `form_name`, `is_organic`, `platform`, `email`, `full_name`,
  `phone_number` (`p:+55...`), `company_name` e as respostas do formulário. O n8n descarta os IDs, o
  e-mail e as respostas. Por gravar direto no banco, o lead entra sem histórico, sem dedup, sem
  telefone normalizado e sem webhooks. O token do uazapi está em texto puro no nó.
- **Funil da Smart Data (empresa 2, pipeline `default`):** Contatos (1) → Qualificado (2) →
  Pré Reunião (3) / Reunião de Levantamento (3) → Reunião de Vendas (4) → Reunião de Retorno (5) →
  Follow Up (6) → Negociação (9). **Pré Reunião e Reunião de Levantamento têm a mesma ordem (3).**
- **Mudança de estágio** hoje só fica como texto no histórico: `Etapa alterada de "X" para "Y".`
  (registro automático, `ophUsuId` nulo). O registro automático também preenche
  `opoDataUltimoContato`, então esse campo **não** indica contato humano.
- **IA no CRM:** `services/llm/llm_factory.py` (OpenAI, `gpt-4o-mini` por padrão).
- **MCP do CRM:** servidor em `/api/mcp/{chave}` com ferramentas de leitura e escrita, escopos
  `mcp:read`/`mcp:write`.

## 5. O que será construído

### 5.1 Dados da Meta por conjunto e anúncio

Novas tabelas, no padrão `<alias><Campo>` e com `EmpId`:

| Tabela | Conteúdo |
|---|---|
| `meta_ads_conjunto` | id externo, nome, campanha, status efetivo |
| `meta_ads_anuncio` | id externo, nome, conjunto, campanha, status efetivo, motivo de reprovação (texto do `issues_info`/`ad_review_feedback`), data de criação no Meta, primeiro dia com impressão |
| `meta_ads_insight_anuncio_diario` | anúncio × dia: gasto, impressões, alcance, cliques (todos), cliques no link, leads Meta |

Na conta (`meta_ads_conta`) passam a ser guardados o `account_status` e o `disable_reason` da Meta.

A sync diária (fase 1) ganha, na mesma execução e na mesma transação por conta:
- `GET /{act}/adsets` e `GET /{act}/ads` (campos de status e nomes), com paginação já sanitizada;
- `GET /{act}/insights?level=ad&time_increment=1` no mesmo período da campanha;
- `GET /{act}?fields=account_status,disable_reason`.

As métricas por campanha da fase 1 continuam vindo do nível campanha (já conferidas com o
Gerenciador); as de anúncio vêm do nível anúncio. **Frequência não é somável por dia:** a frequência
de 7 dias de cada anúncio é obtida numa chamada agregada (`level=ad`, últimos 7 dias, sem
`time_increment`) feita na avaliação dos alertas, e não é gravada por dia.

Leads Meta por anúncio seguem a mesma regra de prioridade de `action_type` da fase 1.

### 5.2 Rastreio do anúncio no lead

**Na oportunidade**, novas colunas: `opoMetaLeadId` (id do lead na Meta), `opoMetaCampanhaId`,
`opoMetaConjuntoId`, `opoMetaAnuncioId` (ids externos, como chegam), e `opoManId` (FK para
`meta_ads_anuncio`, preenchida pelo vínculo).

**Na API de leads** (`POST /api/v1/leads`), novos campos opcionais: `meta_lead_id`, `campaign_id`,
`adset_id`, `ad_id`. O CRM remove os prefixos da Meta (`l:`, `c:`, `as:`, `ag:`) se vierem, por
defesa, e grava nos campos acima. As respostas do formulário vão para `notes` (já existente).

**Vínculo:** ao receber o lead e ao fim de cada sync, o anúncio é resolvido pelo `ad_id`
(`opoManId`) e a campanha pelo anúncio (`opoMcgId`). Sem `ad_id`, vale o vínculo por nome/id de
campanha da fase 1. Vínculo manual continua tendo prioridade e nunca é sobrescrito.

**Atribuição: primeiro anúncio** (decisão do Carlos). Quando o mesmo lead envia o formulário de novo
vindo de outro anúncio, o crédito (MQL, oportunidade, contrato) continua com o **primeiro** anúncio:
os campos `opoMeta*` e `opoManId` só são preenchidos quando estão vazios; o novo envio fica registrado
no histórico do lead (com o nome do anúncio), sem trocar o vínculo. Isso vale tanto para a API de
leads quanto para a carga retroativa.

**Lead "da Meta"** (regra nova): tem `opoMetaLeadId`, ou `opoMetaAnuncioId`, ou está ligado a uma
campanha (`opoMcgId`). Leads com origem mapeada como Meta (ex.: "Anúncios") **sem nenhum desses
sinais não contam como Meta** — não entram em leads, vendas, CPL nem retorno — e aparecem na lista
**"Origem Anúncios sem registro na Meta"** (seção 5.6) para revisão. A linha "Meta — campanha não
identificada" passa a conter só leads com sinal de Meta cujo anúncio/campanha ainda não foi resolvido.

**Liga por conta, depois da carga retroativa** (decisão minha): a regra nova é uma opção da conta
Meta ("contar só leads com rastreio da Meta"), **desligada por padrão**, para não mudar os números de
outras empresas que não enviam ids (ex.: empresa 4, que só tem o nome da campanha em UTM). Para a
Smart Data ela é ligada **depois** de rodar a carga retroativa; antes disso vale a regra da fase 1
(origem mapeada conta como Meta), para os números não irem a zero no meio do caminho.

**CPL** (decisão minha): o CPL principal passa a ser **investimento ÷ leads reportados pela Meta**,
que é o que o Gerenciador de Anúncios mostra (critério de sucesso 2). O custo por lead do CRM
(investimento ÷ leads CRM) continua como coluna separada, rotulada "Custo por lead CRM". Custo por
MQL, por oportunidade e CAC usam as contagens do CRM.

**Cobertura:** % dos leads da Meta do período com `opoMetaAnuncioId` preenchido; exibida na página
Campanhas e no resumo (meta do critério de sucesso: ≥ 90%).

### 5.3 Fluxo n8n

O fluxo "lead Recebido -> CRM -> Whats Pedro" é alterado (com ok do Carlos no momento de publicar):
1. O nó de INSERT no MySQL é trocado por um `POST /api/v1/leads` com uma chave de integração nova
   (escopo `leads:write`, empresa Smart Data). Corpo: `source` = "Anúncios" (casa com a origem 30
   existente), `external_id` e `meta_lead_id` = id do lead sem `l:`, `name`, `email`, `phone` (sem
   `p:`), `company`, `campaign_id`, `adset_id`, `ad_id` (sem prefixos), `notes` com as respostas do
   formulário e o nome do formulário, `owner_email` do responsável atual (usuário 3).
2. O aviso ao Pedro continua igual.
3. O token do uazapi sai do texto do nó e vai para uma credencial do n8n.
4. Depois da troca, a credencial do n8n com escrita direta no banco do CRM deixa de ser usada por
   este fluxo (removê-la do n8n fica a critério do Carlos, pois outros fluxos podem usá-la).

**Carga retroativa:** um fluxo n8n de execução manual lê a planilha inteira e chama um endpoint novo
`POST /api/v1/leads/rastreio-meta` (escopo `leads:write`) que **só atualiza** leads existentes da
empresa da chave — nunca cria — casando por `meta_lead_id`, depois telefone normalizado, depois
e-mail; grava os ids Meta e devolve contagens de casados, não casados e ambíguos (mais de um lead
casou: não atualiza). Linhas são processadas da mais antiga para a mais nova (`created_time`) e,
pela regra de primeiro anúncio, a primeira que casar com um lead fica com o crédito; as seguintes
não trocam o vínculo. Idempotente: rodar de novo não duplica nada.

### 5.4 Funil por estágio

**Registro de mudança de estágio:** nova tabela `oportunidade_etapa_historico` (oportunidade,
estágio de origem, estágio de destino, data/hora, origem `ui|api|mcp|retroativo`). Toda mudança de
estágio feita pelo CRM (tela, Kanban, API de leads, MCP) grava uma linha — inclusive o estágio
inicial na criação. **Carga retroativa** única: ler os textos `Etapa alterada de "X" para "Y".` do
histórico, casar os nomes com os estágios da empresa naquele pipeline e gravar as transições com a
data do registro; a criação vira transição "nenhum → estágio inicial" na data de criação.

**Configuração por empresa** (nova tabela de configuração do monitoramento, seção 5.8): estágio de
MQL e estágio de oportunidade. Padrão da Smart Data: "Reunião de Levantamento" e "Reunião de
Vendas".

**Regras** (cada etapa conta pela **data da primeira vez** que o lead a atingiu):
- **MQL:** entrou no estágio de MQL ou em estágio do mesmo pipeline com ordem **maior** que a dele;
  ou foi ganho sem nunca ter passado por esses estágios (data = fechamento). Estágios com a **mesma
  ordem** do estágio de MQL (ex.: Pré Reunião) **não** contam.
- **Oportunidade:** mesma regra com o estágio de oportunidade.
- **Contrato:** `opoStatusFechamento = 'ganho'`, data = `opoDataFechamento`, valor = MRR/Projeto
  pelas regras da fase 1.
- Voltar a um estágio anterior não desfaz MQL/oportunidade.

**Tempo até o primeiro contato:** horas entre o recebimento e a primeira interação humana (seção 5.7,
regra "lead sem contato"); média por anúncio e no resumo.

### 5.5 Funil por criativo (F3) — página Campanhas

- A tabela de campanhas passa a expandir: campanha → conjunto → anúncio.
- Colunas por linha: investimento, impressões, cliques, CTR, CPC, leads Meta, CPL (Meta), leads CRM,
  custo por lead CRM, MQLs,
  custo por MQL, oportunidades, custo por oportunidade, contratos, CAC, MRR, projeto, retorno.
- **Contagem por período:** cada etapa conta pelo seu próprio evento no período (lead pela data de
  recebimento, MQL/oportunidade pela data em que atingiu o estágio, contrato pela data de
  fechamento) — mesma lógica de período da fase 1 e do Dashboard. Custo da etapa = investimento do
  período ÷ quantidade da etapa no período.
- Cartões de topo ganham MQLs, custo por MQL e cobertura de rastreio.
- Some o título duplicado (cabeçalho do layout + cartão "Campanhas" repetido).

### 5.6 Revisão de origem

Seção na página Campanhas: leads do período com origem mapeada como Meta e **sem sinal de Meta**
(seção 5.2), com nome, data e link para o lead, para alguém corrigir a origem. Não entram em nenhum
indicador de Meta.

### 5.7 Alertas (F2)

Tabela de alertas por empresa: tipo, chave do alvo (anúncio, conta ou lead), status
`aberto | ciente | resolvido`, mensagem, dados numéricos, datas. **Um alerta aberto por (tipo,
alvo)**: enquanto a condição continuar, o alerta é atualizado, não duplicado; quando a condição
deixa de valer na avaliação seguinte, vira `resolvido`. "Ciente" esconde o alerta da lista até ele
ser resolvido e voltar a disparar.

| Alerta | Regra | Avaliação |
|---|---|---|
| CPL fora do padrão | CPL de ontem do anúncio > **1,5×** o CPL dos 7 dias anteriores a ontem; exige ≥ 1 lead ontem e ≥ 1 lead na base | após a sync diária |
| Gasto sem retorno | anúncio gastou ≥ **R$ 150** nos últimos 7 dias sem nenhum lead Meta | após a sync diária |
| Criativo saturando | frequência dos últimos 7 dias > **3** | após a sync diária |
| Queda de CTR | CTR dos últimos 7 dias ≥ **30%** abaixo do CTR dos 7 primeiros dias com impressão do anúncio; só para anúncio com 14+ dias de veiculação e 1.000+ impressões em cada janela | após a sync diária |
| Anúncio parado | anúncio reprovado ou com problemas; conta com status diferente de ativa (ex.: pagamento pendente, desativada); campanha ativa sem impressão ontem | **de hora em hora** (chamada leve de status) e após a sync |
| Lead sem contato | lead da Meta aberto, recebido há mais de **24 h**, sem interação humana | **de hora em hora** |

Leads usados nos alertas de CPL e gasto: leads reportados pela Meta (mais rápidos que os do CRM).

**Interação humana** (para "lead sem contato" e tempo até o primeiro contato): o lead **sair do
estágio inicial** ("Contatos"), um registro no histórico feito por usuário (`ophUsuId` não nulo —
tela ou MCP), ou fechamento. Registros automáticos não contam. O Carlos confirmou que o primeiro
contato será registrado movendo o cartão (o mesmo hábito que o funil já exige).

**Sem backlog** (decisão minha): "lead sem contato" só considera leads recebidos **depois** da data
em que o alerta foi ligado, para não disparar de uma vez por todos os leads antigos.

**Limites** editáveis por empresa (seção 5.8). Os valores acima são o ponto de partida; o Pedro
calibra nas duas primeiras semanas. "Lead sem contato" é o único alerta que mostra nome e telefone.

### 5.8 Configuração do monitoramento

Uma tela de configuração (admin) por empresa com: estágio de MQL, estágio de oportunidade, os
limites dos seis alertas, liga/desliga de cada alerta, horário do resumo (padrão 8h) e valor mínimo
de gasto para um anúncio entrar no ranking do resumo.

### 5.9 Resumo diário (F1) — tela "Monitoramento"

- Gerado **em dia útil (segunda a sexta), às 8h** (America/Sao_Paulo), depois da sync das 4h, para a
  empresa com conta ativa; guardado por data, com botão "gerar de novo" e navegação pelos dias
  anteriores.
- **"Dia anterior" na segunda-feira = sexta a domingo** (decisão minha), para nenhum dia ficar sem
  resumo; a comparação usa a média diária desse período.
- Conteúdo: dia anterior e últimos 7 dias — gasto, leads (Meta e CRM), CPL, MQLs, custo por MQL,
  cobertura; tabela por campanha e por anúncio; **3 melhores e 3 piores anúncios** dos últimos 7
  dias (só anúncios com gasto ≥ mínimo configurado; ordenados por custo por MQL, desempate por CPL;
  anúncio sem lead fica entre os piores pelo gasto); alertas abertos.
- **Leitura**: um ou dois parágrafos gerados pela IA do CRM a partir **só de números agregados**
  (sem dados pessoais), dizendo o que mudou e o que vale olhar. Sem IA configurada ou em erro, o
  resumo sai sem a leitura e avisa.
- A tela "Monitoramento" (menu CRM) reúne: resumo do dia, lista de alertas abertos (com "ciente") e
  link para a página Campanhas.

### 5.10 Perguntas sob demanda (F4)

Novas ferramentas de leitura no MCP do CRM (escopo `mcp:read`): resumo de campanhas por período,
funil por criativo por período, alertas abertos e resumo diário de uma data. Sem dados pessoais nas
respostas. O chat dentro do CRM fica para depois.

### 5.11 Segurança do token

"Testar conexão" e o início de cada sync consultam as permissões do token na Meta
(`GET /me/permissions`). Se houver **qualquer permissão de escrita** (`ads_management`,
`business_management`, `pages_manage_ads` ou qualquer `*_manage_*`/`publish_*`), o teste responde
"token com permissão de escrita — gere um token só leitura" e a sync não roda (status próprio da
conta). Só leitura (`ads_read`, `read_insights`) passa.

## 6. Restrições

- Mesmas restrições da fase 1: isolamento por empresa em toda consulta; rotas de configuração só
  para admin; token nunca em URL, log ou resposta; mensagens em português; SQLite em memória para os
  testes que precisam de SQL; migration só roda com ok do Carlos (o banco do `.env` é o real).
- Nenhuma escrita na Meta, em nenhuma circunstância.
- Dados pessoais de lead só no alerta "lead sem contato" e na lista de revisão de origem.
- A alteração do fluxo n8n publicado e a execução da carga retroativa exigem ok explícito do Carlos
  no momento.

## 7. Deixado para quem implementa

- Nomes de tabelas/colunas e aliases (seguindo `docs/DATABASE_GUIDELINES.md`).
- Onde rodar as avaliações de hora em hora (o worker da fase 1 ganha um segundo ciclo, ou um worker
  novo no mesmo modelo).
- Layout das telas "Monitoramento" e de configuração, seguindo o padrão visual das telas atuais.
- Texto do prompt da leitura do resumo.
- Como reaproveitar ou estender o vínculo e os indicadores da fase 1 sem duplicar regra.

## 8. Decisões que tomei (Claude) e que o Carlos pode trocar

1. Limites iniciais: gasto sem retorno **R$ 150 em 7 dias**; lead sem contato **24 h corridas**.
2. Resumo em dia útil às **8h**, sem considerar feriados.
3. Alertas de CPL e gasto usam leads reportados pela Meta, não os do CRM.
4. Ranking dos 3 melhores/piores por custo por MQL, desempate por CPL, com gasto mínimo.
5. Contagem do funil por evento no período (não por safra de leads).
6. "Interação humana" = histórico feito por usuário, mudança de estágio ou fechamento.
7. Estágios com a mesma ordem do estágio de MQL (Pré Reunião) não contam como MQL.
8. Carga retroativa casa por id do lead na Meta, depois telefone, depois e-mail; ambíguo não atualiza.
9. Perguntas sob demanda primeiro pelo MCP.
10. Verificação de permissões do token também no início de cada sync, não só no teste.
11. Regra nova de "lead da Meta" como opção por conta, desligada por padrão, ligada para a Smart
    Data depois da carga retroativa.
12. CPL principal = investimento ÷ leads da Meta (bate com o Gerenciador); custo por lead do CRM em
    coluna separada.
13. Resumo de segunda-feira cobre de sexta a domingo.
14. "Lead sem contato" ignora leads recebidos antes de o alerta ser ligado.

Decididos pelo Carlos na revisão: atribuição ao **primeiro anúncio**; primeiro contato registrado
**movendo o cartão** para fora de "Contatos".
