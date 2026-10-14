# Meta Ads — Campanhas, custo e retorno — Especificação de design

- **Data:** 14/10/2026
- **Autor:** Carlos Souza (com Claude)
- **Status:** implementada

## 1. Objetivo

Trazer para o SDCRM os resultados das campanhas do Meta Ads **de cada empresa** e cruzá-los com
os leads do CRM, para responder: quanto cada campanha custou, quantos leads e vendas trouxe, a
que custo, e quanto de receita gerou por real investido.

### Critérios de sucesso

1. Um admin conecta uma conta de anúncios (id `act_...` + token de System User) na tela de
   Integrações, testa a conexão e vê nome e moeda da conta.
2. A sincronização diária grava investimento, impressões, cliques, alcance e leads reportados
   pelo Meta por **campanha × dia**, sem intervenção manual.
3. Leads cujo campo UTM/origem externa traz o nome ou id de uma campanha ficam ligados a ela
   automaticamente; leads das origens marcadas como Meta sem campanha identificável aparecem no
   balde "Meta — campanha não identificada".
4. A página Campanhas mostra, por período, investimento, CPL, vendas, CAC, MRR, projeto e
   retorno por campanha; os números de leads, vendas e MRR batem com os do Dashboard para o
   mesmo conjunto de oportunidades.
5. O Dashboard exibe a faixa Meta Ads (investimento, CPL, CAC, retorno) quando a empresa tem
   conta conectada.

### Fora de escopo (desta fase)

- Receber leads do formulário nativo do Meta (Lead Ads / webhook `leadgen`).
- Nível de conjunto de anúncios (adset) e de anúncio (ad).
- OAuth "Conectar com Facebook" e App Review.
- Ferramentas MCP de campanhas.
- Corrigir o Zapier/planilha que hoje grava o nome da campanha em `opoUtmSource`.

## 2. Decisões tomadas

| Decisão | Escolha | Motivo |
|---|---|---|
| Escopo | Custo, retorno e indicadores das campanhas | Escolha do Carlos. Lead Ads fica para depois. |
| Conexão | Token de System User colado por conta, por empresa, criptografado | Funciona já, sem App Review. Modelo do Adverse, mas por empresa e não global. |
| Contas por empresa | Várias | Uma empresa pode ter mais de uma conta de anúncios. |
| Granularidade | Campanha × dia | Os leads hoje só trazem o nome da campanha; descer a anúncio não teria vínculo. |
| Vínculo lead → campanha | Automático por nome/id da campanha nos campos UTM/origem externa; ajuste manual preservado | Dados reais: empresa 4 traz o nome da campanha em `opoUtmSource`; empresa 2 não traz UTM nenhuma. |
| Leads sem campanha | Contam no total da conta via origens marcadas como Meta | Dá CPL geral mesmo para quem não tem UTM (empresa 2, origem "Anúncios"). |
| Agendamento | Worker asyncio no lifespan, como `webhook_worker` | Backend roda um único processo uvicorn; não exige container novo nem mudança de deploy. |
| Janela | Diária às 4h regravando 30 dias; carga inicial de 90 dias | O Meta revisa números retroativamente pela janela de atribuição. |
| Retorno | (MRR × 12 + Projeto) ÷ Investimento | Escolha do Carlos: receita do 1º ano por real investido. |
| Onde aparece | Página nova "Campanhas" + faixa no Dashboard + campo no detalhe do lead | Escolha do Carlos. |

## 3. Modelo de dados

Migration `0030_meta_ads`. Todas as tabelas seguem o padrão `<alias><Campo>`, com `EmpId`,
`Ativo`, `DataCriacao`, `DataAtualizacao` onde se aplica.

### 3.1 `meta_ads_conta` (alias `mac`)

| Coluna | Tipo | Observação |
|---|---|---|
| `macId` | int PK | |
| `macEmpId` | FK `empresa.empId` | |
| `macNome` | varchar(150) | Nome dado pelo usuário; preenchido com o nome do Meta no teste se vazio |
| `macContaExterna` | varchar(40) | Normalizado: só dígitos, prefixado com `act_` |
| `macToken` | text | Token cifrado (Fernet, prefixo `enc:v1:`). Nunca sai pela API |
| `macTokenFinal` | varchar(4) | Últimos 4 caracteres, para exibir "••••1234" |
| `macMoeda` | varchar(3) | Da conta no Meta |
| `macFuso` | varchar(60) | `timezone_name` da conta no Meta |
| `macStatus` | varchar(20) | `pendente` / `sincronizando` / `ok` / `aviso` / `erro` |
| `macMensagem` | varchar(500) | Último erro ou aviso |
| `macUltimaSync` | datetime | Fim da última sync bem-sucedida |
| `macCargaInicialFeita` | bool | Controla a carga de 90 dias |
| `macAtivo` + auditoria | | Inativar para a sync e mantém o histórico |

Único: (`macEmpId`, `macContaExterna`).

### 3.2 `meta_ads_conta_origem` (alias `mco`)

| Coluna | Observação |
|---|---|
| `mcoId` | PK |
| `mcoMacId` | FK `meta_ads_conta.macId`, cascade delete |
| `mcoCcoId` | FK `como_conheceu.ccoId` |

Único: (`mcoMacId`, `mcoCcoId`). A origem deve ser da mesma empresa da conta.

### 3.3 `meta_ads_campanha` (alias `mcg`)

| Coluna | Observação |
|---|---|
| `mcgId` | PK |
| `mcgEmpId` | FK empresa (denormalizado para filtro) |
| `mcgMacId` | FK conta |
| `mcgCampanhaExterna` | id da campanha no Meta (varchar(40)) |
| `mcgNome` | Nome atual; atualizado a cada sync |
| `mcgNomeNormalizado` | Nome normalizado pela regra da seção 5 — usado no vínculo |
| `mcgObjetivo` | `objective` do Meta |
| `mcgStatus` | `effective_status` do Meta |
| auditoria | |

Único: (`mcgMacId`, `mcgCampanhaExterna`). Índice em (`mcgEmpId`, `mcgNomeNormalizado`).

### 3.4 `meta_ads_insight_diario` (alias `mid`)

| Coluna | Observação |
|---|---|
| `midId` | PK |
| `midEmpId`, `midMacId`, `midMcgId` | FKs |
| `midData` | date, no fuso da conta |
| `midInvestimento` | numeric(14,2) — `spend` |
| `midImpressoes`, `midCliques`, `midAlcance` | int — `impressions`, `clicks`, `reach` |
| `midLeadsMeta` | int — soma das ações do tipo lead (ver 4.2) |

Único: (`midMcgId`, `midData`). Índice em (`midEmpId`, `midData`).

### 3.5 `meta_ads_sync_log` (alias `msl`)

`mslId`, `mslMacId`, `mslInicio`, `mslFim` (período sincronizado), `mslOrigem`
(`agendada` / `manual` / `carga_inicial`), `mslStatus` (`ok` / `aviso` / `erro`), `mslLinhas`,
`mslLeadsVinculados`, `mslErro`, `mslDataExecucao`, `mslDuracaoMs`.

### 3.6 Colunas novas em `oportunidade`

| Coluna | Observação |
|---|---|
| `opoMcgId` | FK `meta_ads_campanha.mcgId`, nullable, `ON DELETE SET NULL` |
| `opoMcgManual` | bool, default false. True quando um usuário escolheu a campanha (ou escolheu "nenhuma") na tela |

## 4. Sincronização

### 4.1 Disparo

- **Agendada:** worker `backend/workers/meta_ads_worker.py`, task asyncio iniciada no lifespan,
  mesmo modelo do `webhook_worker` (trabalho pesado em `run_in_threadpool`). Roda 1× por dia na
  hora `META_ADS_SYNC_HORA` (padrão 4, fuso `America/Sao_Paulo`) para todas as contas ativas
  com status diferente de `erro` por token inválido. Flag `META_ADS_SYNC_ENABLED` (padrão true).
- **Janela agendada:** `hoje − 30` até `hoje` (dias no fuso da conta). Se
  `macCargaInicialFeita = false`, usa `hoje − 90` e marca a flag ao concluir.
- **Manual por conta:** `POST /api/meta-ads/contas/{macId}/sincronizar` — enfileira e responde
  `202` imediatamente. Usa a mesma janela da agendada.
- **Reprocessar período:** `POST /api/meta-ads/sincronizar-periodo` com `data_inicial`,
  `data_final` (máx. 366 dias) e `macId` opcional — enfileira e responde `202`.
- **Concorrência:** uma conta nunca sincroniza duas vezes ao mesmo tempo. Ao iniciar, o status
  vai para `sincronizando` com um `UPDATE ... WHERE macStatus <> 'sincronizando'`; se nenhuma
  linha mudou, a requisição responde `409`. Um status `sincronizando` com mais de 30 min é
  considerado travado e liberado.

### 4.2 Chamadas à Graph API

Cliente `backend/services/meta_ads/cliente_graph.py` sobre `httpx` (síncrono), versão em
`META_API_VERSION`, timeout 60s, token no cabeçalho `Authorization: Bearer`.

1. **Teste / dados da conta:** `GET /{act_id}?fields=name,currency,timezone_name,account_status`.
2. **Campanhas:** `GET /{act_id}/campaigns?fields=id,name,objective,effective_status&limit=500`,
   seguindo `paging.next`.
3. **Insights:** `GET /{act_id}/insights` com `level=campaign`, `time_increment=1`,
   `time_range={since,until}`, `fields=campaign_id,campaign_name,spend,impressions,clicks,reach,actions`,
   `limit=500`, seguindo `paging.next`. Campanhas que aparecem nos insights mas não na lista de
   campanhas (ex.: excluídas) são criadas com o nome vindo do insight.
4. **Leads Meta:** soma de `actions[]` cujo `action_type` está em
   `{"lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead"}`, contando
   **apenas o primeiro que existir nessa ordem de prioridade** para não somar o mesmo lead duas
   vezes (o Meta reporta o mesmo lead em mais de um tipo).

### 4.3 Erros

| Situação | Comportamento |
|---|---|
| Código 190 (token inválido/expirado) ou 200/10 (sem permissão na conta) | Status `erro`, mensagem clara ("Token inválido ou expirado — gere um novo no Business Manager"). Agendada pula a conta até o token ser trocado (PUT do token volta o status para `pendente`). |
| Códigos 4, 17, 32, 613, 80004 (limite) e HTTP 5xx / timeout | Até 3 novas tentativas com espera de 30s, 60s, 120s. Esgotou: status `aviso`; a próxima execução agendada recupera a janela. |
| Qualquer outro erro | Status `erro` com a mensagem do Meta; não afeta as demais contas. |

Toda execução grava uma linha em `meta_ads_sync_log`. Token nunca aparece em log nem mensagem.

### 4.4 Gravação

Numa única transação por conta: upsert das campanhas; `DELETE` de `meta_ads_insight_diario`
da conta no período; `INSERT` das linhas recebidas; atualização de `macStatus`, `macMensagem`,
`macUltimaSync`. Falha no meio: rollback, nada parcial fica gravado.

## 5. Vínculo lead → campanha

Serviço `backend/services/meta_ads/vinculo.py`.

**Normalização:** `strip`, minúsculas, espaços internos colapsados para um. (Sem remover
acentos ou pontuação: os nomes de campanha usam `|` como separador.)

**Candidatos de texto do lead:** `opoUtmCampaign`, `opoUtmSource`, `opoUtmContent`,
`opoUtmTerm`, `opoOrigemExternalId` (os não vazios).

**Regra:** para cada candidato normalizado, procura na empresa do lead uma campanha com
`mcgCampanhaExterna == candidato` ou `mcgNomeNormalizado == candidato`. Se exatamente **uma**
campanha casar (considerando todos os candidatos), liga. Zero ou mais de uma: não liga.

**Quando roda:**
- Ao criar/atualizar lead pela API de entrada (`lead_intake_service`), após gravar.
- Ao fim de cada sync, para as oportunidades da empresa com `opoMcgId IS NULL` e
  `opoMcgManual = false` que tenham algum candidato preenchido.

**Manual:** `PATCH` da oportunidade com `opoMcgId` (inclusive `null`) grava `opoMcgManual = true`.
O automático nunca altera oportunidades com `opoMcgManual = true`.

**Lead "do Meta":** oportunidade com `opoMcgId` não nulo **ou** com `opoCcoId` entre as origens
mapeadas em qualquer conta ativa da empresa.

## 6. Indicadores

Mesmas condições de data e de status do Dashboard (`_query_rankings_analiticos`), filtrando
`opoAtivo = true` e a empresa:

| Indicador | Definição |
|---|---|
| Investimento | `SUM(midInvestimento)` com `midData` no período |
| Impressões, Cliques, Alcance | Somas no período. CTR = cliques ÷ impressões; CPC = investimento ÷ cliques |
| Leads Meta | `SUM(midLeadsMeta)` no período |
| Leads CRM | Oportunidades do Meta com `opoDataRecebimento` no período |
| CPL | Investimento ÷ Leads CRM (0 leads → exibe "—") |
| Vendas | Oportunidades do Meta com `opoStatusFechamento = 'ganho'` e `opoDataFechamento` no período |
| CAC | Investimento ÷ Vendas |
| MRR / Projeto | `_mrr_incremental_expr()` / `_valor_projeto_expr()` somados sobre as vendas (reaproveitados do `crm_dashboard_service`) |
| Retorno | (MRR × 12 + Projeto) ÷ Investimento, exibido como "4,2×" |

**Linhas da tabela:** uma por campanha que teve investimento **ou** lead no período; a linha
"Meta — campanha não identificada" (leads do Meta com `opoMcgId IS NULL`, investimento 0); e a
linha **Total**, cujo investimento é o de todas as campanhas e cujos leads/vendas incluem os não
identificados (cada oportunidade contada uma vez).

Filtro por conta (`macId`) restringe investimento às campanhas da conta e leads às campanhas da
conta + leads não identificados das origens mapeadas naquela conta.

## 7. API

Rotas internas em português, JWT + `CompanyIdDep` + `require_user_in_company`.

**Admin (`require_admin`):**

| Método e rota | Função |
|---|---|
| `GET /api/meta-ads/contas` | Lista contas da empresa (sem token; com `macTokenFinal`, status, última sync, origens) |
| `POST /api/meta-ads/contas` | Cria conta (nome, conta externa, token, origens) |
| `PUT /api/meta-ads/contas/{macId}` | Edita nome, origens, ativo; token só se enviado |
| `POST /api/meta-ads/contas/{macId}/testar` | Chama o Meta, devolve nome/moeda/fuso e grava moeda e fuso |
| `POST /api/meta-ads/contas/{macId}/sincronizar` | Sync manual (202) |
| `POST /api/meta-ads/sincronizar-periodo` | Reprocessar período (202) |
| `GET /api/meta-ads/contas/{macId}/logs` | Últimas execuções |

**Usuários da empresa:**

| Método e rota | Função |
|---|---|
| `GET /api/meta-ads/painel?data_inicial&data_final&macId&somente_ativas` | Cards + linhas da tabela (seção 6) + `temConta` |
| `GET /api/meta-ads/campanhas/{mcgId}?data_inicial&data_final` | Série diária (investimento, leads Meta, leads CRM) + lista de leads da campanha |
| `GET /api/meta-ads/resumo?data_inicial&data_final` | Faixa do Dashboard: investimento, CPL, CAC, retorno, `temConta` |
| `GET /api/meta-ads/campanhas-opcoes` | Campanhas da empresa para o seletor do detalhe do lead |

`opoMcgId` passa a constar no schema de resposta/atualização de oportunidade.

## 8. Telas

- **Integrações → aba "Meta Ads"** (admin): lista de contas com status colorido, "••••1234",
  última sync e mensagem; formulário de conta (nome, `act_...`, token, multi-seleção de origens);
  botões Testar conexão, Sincronizar agora, Ver log; ação de reprocessar período.
- **Página "Campanhas"** (`/campanhas`, item novo no menu): filtros de período (mesmo componente
  do Dashboard), conta e "só ativas"; cards Investimento · Leads CRM · CPL · Vendas · CAC · MRR ·
  Retorno; tabela da seção 6 ordenada por investimento; clique numa campanha abre painel lateral
  com gráfico diário (barras de investimento, linha de leads) e lista de leads com link para a
  oportunidade. Sem conta: estado vazio com link para Integrações (admin) ou aviso (não admin).
- **Dashboard:** faixa "Meta Ads" com 4 cards, só quando `temConta`; usa o período do filtro do
  Dashboard; link "ver campanhas".
- **Detalhe da oportunidade:** campo "Campanha Meta" (select com as campanhas + "Nenhuma"),
  com indicação "vinculada automaticamente" quando `opoMcgManual = false`.

## 9. Configuração

Novas variáveis em `config.py` / `.env.example`:

| Variável | Padrão |
|---|---|
| `META_API_VERSION` | versão estável vigente da Graph API no momento da implementação |
| `META_ADS_SYNC_ENABLED` | `true` |
| `META_ADS_SYNC_HORA` | `4` |
| `SECRETS_ENCRYPTION_KEY` | opcional; ausente usa `JWT_SECRET_KEY` (modelo do Adverse) |

`cryptography` passa a ser fixado em `requirements.txt` (hoje vem por `python-jose[cryptography]`).

## 10. Testes

- **Cliente Graph:** paginação, extração de leads com prioridade de `action_type`, mapeamento dos
  códigos 190/limite/5xx, token ausente de URLs e mensagens (`httpx.MockTransport`).
- **Sync:** regravação do período sem sobras; rollback em falha; campanha só nos insights é
  criada; carga inicial de 90 dias uma vez; trava de concorrência e liberação após 30 min.
- **Vínculo:** casamento por nome (maiúsculas, espaços), por id, ambiguidade não liga, manual
  preservado, escopo por empresa.
- **Indicadores:** CPL/CAC/retorno com divisões por zero; linha "não identificada"; total sem
  dupla contagem; leads, vendas e MRR iguais aos da aba Fontes do Dashboard para as mesmas
  oportunidades.
- **API:** token nunca retornado; rotas de admin bloqueadas para não admin; isolamento entre
  empresas.
- **Cripto:** ida e volta do token; chave trocada não quebra a listagem (token vira "inválido").

## 11. Ajustes na implementação

1. **Status `token_invalido` e coluna `macSyncIniciadaEm`.** A spec usa `erro` para token inválido e diz que a agendada "pula a conta até trocar o token" — sem um status próprio não há como distinguir token inválido de erro comum (que deve tentar de novo no dia seguinte). `macSyncIniciadaEm` guarda quando a trava foi pega, para liberar travas mortas após 30 min.
2. **Sync manual em `BackgroundTasks`.** O worker cuida só da rodada diária; o clique em "Sincronizar agora" pega a trava na própria requisição (409 se ocupada) e roda a sync após a resposta. Mesmo efeito da spec, sem fila em memória.
3. **Vínculo manual em rota própria** `PATCH /api/meta-ads/oportunidades/{opo_id}/campanha`, e não no `PUT /api/oportunidades/{id}` (a tela de detalhe envia o formulário inteiro no PUT; misturar quebraria a marca de "manual").
4. **MRR/Projeto com a regra da aba Fontes.** A spec diz "somados sobre as vendas"; a aba Fontes soma o MRR das ganhas **recebidas ou fechadas** no período. Para cumprir o critério de sucesso 4 (números batendo), as condições de período viram um helper compartilhado `condicoes_periodo` no `crm_dashboard_service`.
5. **Integrações → página própria** `/integracoes/meta-ads` (o menu Integrações usa páginas, não abas).
6. **Alcance** é gravado mas não exibido: alcance diário não é somável.
7. **Origem no log:** `agendada`, `manual`, `periodo`, `carga_inicial`.
8. **Detalhe da campanha em `Modal`** (componente existente) em vez de painel lateral.
9. **Rota extra** `GET /api/meta-ads/contas-opcoes` (não admin), para o filtro de conta da página Campanhas.
10. Versão padrão da Graph API: `v26.0` (conferida no changelog do Meta na implementação).
