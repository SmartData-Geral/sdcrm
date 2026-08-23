# Integração externa — API de entrada de leads

Superfície pública do CRM, autenticada por chave de API. Hoje alimentada pelo Zapier a
partir da planilha de leads; o mesmo endpoint serve Meta Lead Ads, formulário do site ou
qualquer outra fonte, sem mudança no CRM.

## Por que `/api/v1/` e não `/api/leads`

Exceção deliberada à convenção de [API_GUIDELINES.md](API_GUIDELINES.md). Este é um
contrato consumido por terceiros: precisa de versionamento explícito para poder evoluir
sem quebrar integrações, e usa nomes de campo em inglês, que é o que ferramentas de
automação esperam. As rotas internas do CRM seguem em português e sem versão.

## Endpoints

| Método | Rota | Escopo |
|---|---|---|
| GET | `/api/v1/ping` | qualquer |
| POST | `/api/v1/leads` | `leads:write` |

URL pública: `https://smartdata.app.br/crm/api/v1/leads`
(o nginx já mapeia `/crm/api/` para o backend — nenhuma configuração adicional.)

Autenticação: header `X-API-Key`. **Estas rotas não usam `X-Company-Id`** — a empresa
vem da própria chave. Um `X-Company-Id` divergente é ignorado.

## POST /api/v1/leads

```json
{
  "source": "planilha_leads",
  "external_id": "row_8842",
  "name": "Maria Silva",
  "company": "ACME",
  "email": "maria@exemplo.com",
  "phone": "+55 41 99999-0000",
  "utm_source": "meta",
  "utm_campaign": "leadgen_ago26",
  "notes": "Interesse no ScaleX",
  "owner_email": "vendedor@smartdatabi.com.br",
  "value": 3500
}
```

`source` é obrigatório. `email` **ou** `phone` é obrigatório — os demais são opcionais.
Aceita também os nomes em português `origem`, `nome`, `empresa`, `telefone`, `observacoes`.

### Respostas

| Código | Quando |
|---|---|
| `201` | lead novo criado |
| `200` | lead já existia e foi atualizado |
| `401` | chave ausente, inválida, expirada ou revogada |
| `403` | chave sem o escopo `leads:write` |
| `409` | outro processo está tratando o mesmo lead; pode repetir |
| `422` | payload inválido (sem `source`, ou sem e-mail e sem telefone utilizáveis) |

```json
{
  "lead_id": "ld_193",
  "status": "created",
  "opportunity_id": 193,
  "deduped_by": null,
  "previous_cycle_lead_id": null,
  "url": "https://smartdata.app.br/crm/oportunidades/193"
}
```

`lead_id` mantém o formato do contrato original; `opportunity_id` é o identificador real
dentro do CRM, sem prefixo para remover.

## O que acontece com o lead

Um lead **é** uma oportunidade neste CRM. Ele nasce na etapa "Novo Lead" do pipeline
`default`, com `source` gravado em `opoOrigemSistema` e mapeado para "Como conheceu".

### Deduplicação

Na ordem:

1. **`external_id`** — mesma `source` e mesmo `external_id` numa oportunidade aberta.
   É o sinal mais forte: é literalmente a mesma linha da planilha voltando.
2. **E-mail ou telefone normalizado**, entre as oportunidades **abertas** da empresa.

Telefones são comparados na forma canônica `55 + DDD + número`, com o 9º dígito inserido
nos celulares. Então `+55 41 99999-0000`, `(41) 99999-0000` e `41 9999-0000` são o mesmo
contato. Número sem DDD não participa do dedup — casaria com meio Brasil.

### Quando o ciclo anterior está fechado

Se o único registro encontrado está ganho, perdido ou em stand-by, **uma nova
oportunidade é criada**, com `opoOpoAnteriorId` apontando para a anterior e um registro
no histórico dos dois lados. A resposta traz `previous_cycle_lead_id`. Isso preserva as
métricas de ganho e perda do dashboard.

### O que a integração nunca sobrescreve

Etapa, responsável, status de fechamento, valores, lead score, temperatura, produto e
comentários são trabalho humano e ficam intocados numa atualização. Dados de contato só
são preenchidos se estiverem vazios; divergência vira observação no histórico, não
sobrescrita.

## Configuração no Zapier

**Zap de entrada:**

1. Trigger: *Google Sheets → New Spreadsheet Row* (use *New or Updated Spreadsheet Row*
   se edições também devem fluir).
2. Action: *Webhooks by Zapier → POST*
   - URL: `https://smartdata.app.br/crm/api/v1/leads`
   - Payload Type: **json**
   - Data: mapeie as colunas da planilha para os campos acima
   - Headers: `X-API-Key` com a chave, `Content-Type: application/json`
   - Unflatten: **no**

Duas armadilhas: *New Spreadsheet Row* só dispara em linhas novas, não em edições; e
**crie uma coluna de ID estável na planilha e mapeie para `external_id`** — sem ela, o
sinal mais forte de deduplicação fica indisponível.

`Webhooks by Zapier` é recurso de plano pago — confirme o plano antes de montar o Zap.

## Chaves de API

Criadas em Integrações → Chaves de API (somente admin), ou via API:

```bash
curl -X POST https://smartdata.app.br/crm/api/integracao-chaves \
  -H "Authorization: Bearer $JWT" -H "X-Company-Id: 1" \
  -H "Content-Type: application/json" \
  -d '{"ichNome":"Zapier - Planilha de Leads","escopos":["leads:write"]}'
```

A chave em texto puro aparece **uma única vez**, na resposta da criação. Ela não é
armazenada — o banco guarda só o prefixo público e um HMAC-SHA256 do segredo. Perdeu,
revoga e emite outra.

`API_KEY_PEPPER` precisa estar definido no `.env` em produção. **Trocar esse valor
invalida todas as chaves já emitidas.**

Revogação (`POST /api/integracao-chaves/{id}/revogar`) tem efeito imediato.

## Log de requisições

Toda chamada a `/api/v1/*` é registrada, inclusive 401 e 422, em
`GET /api/integracao-logs`. E-mail e telefone aparecem mascarados e a chave nunca é
gravada — só o prefixo. Campos fora da allowlist têm apenas o **nome** registrado.

Retenção padrão: 90 dias (`INTEGRACAO_LOG_RETENCAO_DIAS`). O log contém PII de lead —
a retenção é o controle de LGPD.

---

# Webhooks de saída (Fase 2)

O CRM avisa sistemas externos quando algo acontece. Configurado em **Integrações →
Webhooks** (somente admin).

## Catálogo de eventos

| Evento | Prio | Dispara quando |
|---|---|---|
| `lead.created` | P0 | Lead entra pela API `/api/v1/leads` |
| `lead.updated` | P1 | Lead existente é atualizado pela API |
| `deal.created` | P1 | Oportunidade criada **pela tela** do CRM |
| `deal.stage_changed` | P0 | Oportunidade muda de etapa |
| `deal.won` | P0 | Marcada como ganha |
| `deal.lost` | P1 | Marcada como perdida |
| `deal.standby` | P3 | Colocada em stand-by |
| `deal.contact_updated` | P2 | Nome, e-mail, telefone ou empresa do contato mudou |
| `task.completed` | P2 | **Indisponível** — ver abaixo |

Duas observações que o catálogo original do quadro não previa:

**Lead e deal são a mesma linha.** Neste CRM não existe entidade `lead` separada — um
lead é uma `oportunidade`. Por isso `lead.created` e `deal.created` são **mutuamente
exclusivos**, discriminados pela origem: entrou pela API, é `lead.created`; nasceu na
tela, é `deal.created`. Sem essa regra, toda oportunidade nova dispararia os dois e
dobraria o consumo de tasks do Zapier.

**`task.completed` não tem entidade por trás.** O CRM não possui módulo de tarefas. O
evento aparece no catálogo marcado como indisponível, com o motivo, em vez de sumir da
lista — assim ninguém acha que quebrou. Ele passa a ser emitido no dia em que a entidade
existir. Se o que o time queria era outro sinal, três candidatos já instrumentados:
`reuniao_analise` concluída, aceite de proposta e assinatura de contrato.

**`contact.updated` virou `deal.contact_updated`** pelo mesmo motivo: dados de contato
moram na oportunidade, não numa entidade separada.

## Envelope

```json
{
  "id": "evt_000123",
  "type": "deal.won",
  "created_at": "2026-08-22T14:03:11Z",
  "api_version": "2026-08-01",
  "company_id": 1,
  "data": { "object": "deal", "deal_id": 193, "title": "Maria Silva", "...": "..." },
  "previous_attributes": { "status": null }
}
```

O `data` é **congelado no momento do evento**: uma entrega retentada seis horas depois
reporta o que aconteceu, não o estado atual do registro.

## Assinatura

Headers de toda entrega:

```
X-SDCRM-Event:       deal.won
X-SDCRM-Event-Id:    evt_000123     ← chave de idempotência do consumidor
X-SDCRM-Delivery-Id: dlv_000456
X-SDCRM-Timestamp:   1787654651
X-SDCRM-Signature:   v1=<hex>
```

`v1` é `HMAC-SHA256(segredo, "<timestamp>." + corpo_bruto)` — o mesmo esquema do Stripe.
Verificação em Python:

```python
import hashlib, hmac, time

def verificar(segredo: str, cabecalho: str, timestamp: int, corpo: bytes) -> bool:
    if abs(int(time.time()) - timestamp) > 300:      # proteção contra replay
        return False
    esperado = hmac.new(
        segredo.encode(), f"{timestamp}.".encode() + corpo, hashlib.sha256
    ).hexdigest()
    return any(
        hmac.compare_digest(p.strip()[3:], esperado)
        for p in cabecalho.split(",") if p.strip().startswith("v1=")
    )
```

Assine sobre os **bytes exatos** recebidos. Reserializar o JSON antes de verificar muda
a ordem das chaves ou o espaçamento e a assinatura deixa de bater.

Durante uma rotação de segredo o header traz os dois valores (`v1=novo,v1=antigo`) —
aceite qualquer um.

> O "Catch Hook" do Zapier não verifica assinatura. Para ele, o segredo é a própria URL.
> Use "Catch Raw Hook" + um passo de Code se quiser validar.

## Entrega e retentativas

Tentativas em **30s, 2min, 10min, 1h, 6h, 24h** (7 no total, ~31 horas).

- **Retenta:** erro de rede, timeout, `408`, `429`, `5xx`. Um `Retry-After` menor que o
  backoff é respeitado; maior é ignorado, senão o consumidor poderia adiar para sempre.
- **Não retenta:** `2xx` (sucesso) e demais `4xx` — é contrato quebrado do consumidor.
- **`3xx` não é seguido**: um redirect é vetor de exfiltração do payload assinado, então
  vira falha permanente.
- Após **20 falhas consecutivas** a assinatura é desativada automaticamente, para um Zap
  abandonado não queimar o worker indefinidamente. Reativar zera o contador.

## Segurança da URL de destino

Uma URL de webhook é um primitivo de requisição server-side. Por isso o destino precisa
ser `https` e o host é resolvido e recusado se cair em faixa privada, loopback,
link-local ou multicast — **na gravação e de novo a cada envio**, porque o DNS pode mudar
de resposta no meio (rebinding). `WEBHOOK_HOSTS_PERMITIDOS` restringe ainda mais.

## Como o evento é garantido

O evento é gravado na **mesma transação** da mudança que o originou (padrão outbox). Se o
processo cair no meio, ou os dois existem ou nenhum existe — nunca um webhook de algo que
sofreu rollback, nem uma mudança sem o aviso correspondente.

A entrega roda numa task assíncrona dentro do próprio processo do backend, com poll de
10 segundos. `WEBHOOK_WORKER_ENABLED=false` desliga, caso um dia extraiam um container de
worker dedicado.

## Operação

- **Enviar evento de teste:** botão na tela, valida a configuração do Catch Hook na hora.
- **Ver entregas:** status, tentativas, HTTP, próxima tentativa e trecho da resposta.
- **Reenviar:** força a próxima tentativa imediatamente.
- **Rotacionar segredo:** gera outro; o valor aparece uma única vez.

Retenção das entregas entregues: 30 dias (`WEBHOOK_RETENCAO_DIAS`), podadas pelo mesmo
worker uma vez por hora.
