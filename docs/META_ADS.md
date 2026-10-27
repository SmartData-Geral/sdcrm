# Meta Ads no SDCRM

Mostra investimento, custo por lead, custo por venda e retorno por campanha, cruzando os
dados do Meta Ads com os leads do CRM. Cada empresa conecta as próprias contas.

## Gerar o token (System User)

1. No Business Manager da empresa: **Configurações do negócio → Usuários → Usuários do sistema**.
2. Crie (ou escolha) um usuário do sistema e clique em **Adicionar ativos** → **Contas de anúncios** → marque a conta → permissão **Ver desempenho**.
3. Clique em **Gerar novo token**, escolha um app do negócio e marque a permissão **ads_read**. Prefira validade "Nunca".
4. Copie o token (começa com `EAA`). Ele só aparece uma vez.

O ID da conta fica em **Gerenciador de Anúncios → menu de contas** (número; o CRM aceita com ou sem `act_`).

## Conectar no CRM

**Integrações → Meta Ads → Conectar conta** (somente administradores): nome, ID da conta, token
e as **origens que contam como Meta Ads** (ex.: "Anúncios"). Depois clique em **Testar conexão**
e em **Sincronizar agora** — a primeira sincronização carrega os últimos 90 dias.

## Como o lead é ligado à campanha

O CRM procura o **nome ou o id da campanha** nos campos UTM do lead (`utm_campaign`, `utm_source`,
`utm_content`, `utm_term`) e na origem externa, sem diferenciar maiúsculas e espaços. Liga só se
achar exatamente uma campanha. Leads das origens marcadas como Meta sem campanha identificada
aparecem como "Meta — campanha não identificada". No detalhe do lead dá para escolher a campanha à mão.

Para o vínculo funcionar, configure o Zapier/formulário para enviar o nome da campanha em
`utm_campaign` (hoje a planilha envia em `utm_source`, o que também funciona).

## Limitações conhecidas

- Nível de campanha (não conjunto nem anúncio).
- Valores exibidos como R$, sem conversão de moeda (contas em outra moeda mostram o valor na moeda da conta com o símbolo de R$).
- Formulários nativos do Meta (Lead Ads) não entram automaticamente; continuam vindo pela integração existente.
- Sincronização diária às 4h (`META_ADS_SYNC_HORA`), regravando os últimos 30 dias.

## Monitoramento (resumo diário e alertas)

**CRM → Monitoramento** mostra o resumo do dia útil (gerado às 8h, segunda a sexta; segunda cobre
sexta a domingo), os alertas abertos e, para administradores, a configuração: estágio de MQL
(padrão "Reunião de Levantamento"), estágio de oportunidade (padrão "Reunião de Vendas") e os
limites dos seis alertas (CPL 1,5× a média dos 7 dias anteriores, gasto de R$ 150 em 7 dias sem
lead, frequência acima de 3, CTR 30% abaixo da primeira semana, anúncio/conta parados e lead da
Meta sem contato em 24 h). O primeiro contato conta quando o cartão sai de "Contatos".

Na página **Campanhas**, cada campanha abre em conjuntos e anúncios, com leads, MQLs,
oportunidades, contratos e o custo de cada etapa. O CPL principal é investimento ÷ leads da Meta
(igual ao Gerenciador de Anúncios); o custo por lead do CRM fica em coluna separada.

## Fluxo n8n dos leads do formulário

O fluxo **"lead Recebido -> CRM -> Whats Pedro"** lê a planilha "Codeseller leads face" (exportação
da Meta) e chama `POST /api/v1/leads` com a credencial "SDCRM API - Smart Data" (Header Auth,
`X-API-Key`). Envia `source: "Anúncios"`, o id do lead e os ids de campanha, conjunto e anúncio sem
os prefixos da Meta (`l:`, `c:`, `as:`, `ag:`, `p:`), e as respostas do formulário em `notes`.
O crédito fica sempre com o **primeiro** anúncio do lead.

## Carga retroativa de rastreio

O fluxo manual **"CRM · Carga retroativa de rastreio Meta"** lê a planilha inteira **em ordem
crescente de `created_time`** e chama `POST /api/v1/leads/rastreio-meta` em lotes de 500. Só
atualiza leads existentes (casando por id do lead, telefone e e-mail) e pode ser executado de novo
sem duplicar nada. Ao reexecutar, linhas sem `ad_id` voltam a contar como "casados".

Depois da carga, a conta da Smart Data passou a **contar só leads com rastreio da Meta**
(Integrações → Meta Ads → Editar conta). Leads de origem "Anúncios" sem registro na Meta aparecem
em "Origem Anúncios sem registro na Meta", na página Campanhas, para correção da origem.
