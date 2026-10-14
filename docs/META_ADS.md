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
- Valores exibidos em reais; contas em outra moeda aparecem com o símbolo de R$.
- Formulários nativos do Meta (Lead Ads) não entram automaticamente; continuam vindo pela integração existente.
- Sincronização diária às 4h (`META_ADS_SYNC_HORA`), regravando os últimos 30 dias.
