# MCP do SDCRM — Especificação de design

- **Data:** 27/09/2026
- **Autor:** Carlos Souza (com Claude)
- **Status:** aguardando revisão

## 1. Objetivo

Expor o CRM a agentes de IA (Claude no claude.ai, Claude Code, n8n) por um servidor MCP que
permita **ler e alterar leads/oportunidades, status, etapas e qualificação, registrar
interações e consultar indicadores**, reaproveitando as regras de negócio que já existem no
backend.

### Critérios de sucesso

1. Uma chave de integração com `mcp:read` + `mcp:write`, criada na tela de Integrações, conecta
   o SDCRM como conector no claude.ai e no Claude Code.
2. As 18 ferramentas da seção 5 funcionam contra a empresa da chave, e somente contra ela.
3. Toda alteração feita pelo MCP produz o mesmo histórico e os mesmos webhooks que a mesma
   alteração feita pela tela.
4. Toda chamada de ferramenta aparece no log de requisições de integração.
5. Revogar a chave corta o acesso na chamada seguinte.

### Fora de escopo (desta fase)

- Inativar ou excluir oportunidades.
- Criar/editar metas mensais (metas são só leitura).
- Criar/editar etapas, produtos, origens, motivos de perda e usuários.
- Propostas, contratos, análise de reunião e Smart Agente.
- Token MCP por usuário (modelo do SDFin). A autenticação é só por chave de integração.
- Transporte stdio.

## 2. Decisões tomadas

| Decisão | Escolha | Motivo |
|---|---|---|
| Onde roda | Dentro do backend FastAPI, montado em `/api/mcp` (modelo do SDFin) | Chama os services direto: histórico, webhooks, dedup e isolamento por empresa vêm de graça. A alternativa (processo separado sobre REST) exigiria criar dezenas de endpoints `/api/v1` antes. |
| Autenticação | Chave de integração `sdcrm_…` existente, escopos `mcp:read` / `mcp:write` | Já tem emissão, revogação, expiração, hash com pepper, log e tela. Os escopos já estão reservados em `ESCOPOS_CONHECIDOS`. |
| Em nome de quem grava | Da empresa da chave; anotações manuais usam o responsável padrão da chave | É o mesmo modelo da API de entrada de leads. |
| Escrita permitida | Leads e funil, histórico/interações, fechamento (ganho/perdido/stand-by/reativar) | Escolha do Carlos. Metas ficaram só leitura. |
| SDK | `mcp==2.0.0` (classe `MCPServer`), Streamable HTTP stateless com resposta JSON | Mesma versão e configuração do SDFin, que já funciona como conector no claude.ai. |

## 3. Arquitetura

```
claude.ai / Claude Code / n8n
        │  POST https://<host>/crm/api/mcp/<chave>
        ▼
nginx  (/crm/api/ → crm-backend:8000/api/)
        ▼
FastAPI  app.mount("/api/mcp", build_mcp_asgi_app())
        ▼
AutenticacaoMCPASGI  ── valida a chave, injeta x-sdcrm-ich-id, reescreve o path
        ▼
MCPServer("SDCRM").streamable_http_app(stateless, json_response)
        ▼
@ferramenta(...)  ── sessão de banco, revalida chave, escopo, erros, log
        ▼
services existentes (oportunidade_service, lead_intake_service,
crm_dashboard_service, crm_meta_mensal_service, oportunidade_historico_service, ...)
```

### 3.1 Pacote `backend/mcp_crm/`

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Exporta `mcp` e `build_mcp_asgi_app`. |
| `servidor.py` | Cria `MCPServer(name="SDCRM", title="SDCRM - CRM Smart Data", instructions=..., version="1.0.0")`, importa os módulos de ferramentas (que se registram no import) e define `build_mcp_asgi_app()`. |
| `autenticacao.py` | Wrapper ASGI `AutenticacaoMCPASGI` (seção 4.1). |
| `sessao.py` | `ContextoMCP` (dataclass) e o gerenciador de contexto `abrir_sessao(ctx)` (seção 4.2). |
| `ferramenta.py` | Decorador `@ferramenta(escrita: bool)` (seção 6). |
| `serializacao.py` | Conversão de `Oportunidade`/histórico/etapa para o JSON enxuto (seção 5.3) e resolução de nomes em lote. |
| `ferramentas/contexto.py` | `contexto`, `listar_cadastros` |
| `ferramentas/oportunidades.py` | `buscar_oportunidades`, `obter_oportunidade`, `criar_lead`, `atualizar_oportunidade` |
| `ferramentas/funil.py` | `resumo_funil`, `mover_etapa`, `atualizar_qualificacao` |
| `ferramentas/historico.py` | `listar_historico`, `registrar_interacao` |
| `ferramentas/fechamento.py` | `marcar_ganho`, `marcar_perdido`, `colocar_stand_by`, `reativar_oportunidade` |
| `ferramentas/indicadores.py` | `obter_indicadores`, `detalhar_indicador`, `obter_metas` |

O nome `mcp_crm` evita sombrear o pacote `mcp` do SDK.

### 3.2 Integração com `main.py`

- `app.mount("/api/mcp", build_mcp_asgi_app())` depois dos `include_router`.
- No `lifespan` existente, envolver o `yield` com `async with mcp.session_manager.run():`,
  mantendo o worker de webhooks como está.
- Log de inicialização: `"Servidor MCP disponível em /api/mcp/{chave}"`.

### 3.3 Dependência

`mcp==2.0.0` em `backend/requirements.txt`. A imagem Docker usa Python 3.11 e o ambiente local
usa 3.14: a instalação e os testes devem passar nos dois.

## 4. Autenticação

### 4.1 Wrapper ASGI `AutenticacaoMCPASGI`

Para requisições `http`:

1. Calcula o caminho efetivo dentro do mount, tratando `root_path` como o SDFin faz (com
   `root_path` presente ou com o proxy removendo o prefixo).
2. Obtém a chave, nesta ordem: primeiro segmento do caminho efetivo (`/api/mcp/<chave>/...`) ou,
   se o caminho estiver vazio, o header `X-API-Key`.
3. Autentica com `integracao_chave_service.autenticar(db, chave)` numa `SessionLocal` própria.
4. Recusa com **401** `{"detail": "Chave de API invalida ou revogada"}` (mesma mensagem da API)
   quando a chave não existe, é inválida, revogada, inativa, expirada, **ou não tem nenhum dos
   escopos `mcp:read` / `mcp:write`**. Registra `integracao_log_service.registrar(rota="mcp",
   metodo=<método>, status_http=401, resultado="unauthorized",
   prefixo_informado=prefixo_para_log(chave), ip, user_agent)`.
5. Em caso de sucesso: remove qualquer header de entrada que comece com `x-sdcrm-`, injeta
   `x-sdcrm-ich-id: <ichId>`, reescreve `path`/`raw_path` para o restante após a chave
   (`/` se vazio), zera `root_path` e repassa ao app do MCP.

Requisições que não são `http` (lifespan) passam direto.

### 4.2 Sessão por chamada — `abrir_sessao(ctx)`

Toda ferramenta roda dentro de `abrir_sessao`, que:

1. Lê `x-sdcrm-ich-id` dos headers do contexto MCP. Ausente → erro "Requisição MCP sem
   autenticação. Verifique a URL do conector."
2. Abre `SessionLocal()` e **recarrega a `IntegracaoChave`**, conferindo de novo ativa, não
   revogada, não expirada. Assim, revogar a chave corta o acesso mesmo com uma sessão MCP aberta.
3. Monta `ContextoMCP(db, ichId, empId, nome, escopos, usuResponsavelPadraoId)`. O `empId`
   vem **sempre** da chave; nenhuma ferramenta recebe empresa por parâmetro.
4. Chama `integracao_chave_service.registrar_uso` (que já limita a gravação a uma a cada 5 min).
5. Fecha a sessão no fim; faz `rollback` se houver exceção.

### 4.3 Escopos

- Ferramenta de leitura: exige `mcp:read` **ou** `mcp:write`.
- Ferramenta de escrita: exige `mcp:write`. Sem ele: erro "Esta chave não tem permissão de
  escrita (escopo mcp:write)."

### 4.4 Risco conhecido

A chave vai na URL porque o conector personalizado do claude.ai não envia headers próprios.
Ela pode aparecer em logs de acesso do nginx. Mitigações: o log da aplicação grava só o
prefixo; a documentação orienta a criar uma chave exclusiva para o MCP e revogá-la ao trocar
de conector. É o mesmo risco já aceito no SDFin.

## 5. Ferramentas

As descrições das ferramentas (docstrings) ficam em português e dizem quando usar cada uma.
Datas em `YYYY-MM-DD`, fuso America/Sao_Paulo.

**Instruções do servidor:** "Servidor MCP do CRM SDCRM. Permite consultar e operar leads e
oportunidades, o funil de vendas, o histórico de interações e os indicadores comerciais da
empresa vinculada à chave do conector. Chame `contexto` primeiro e `listar_cadastros` para
descobrir IDs de etapas, produtos, origens, motivos de perda e responsáveis. Antes de marcar
ganho, perdido, stand-by ou reativar, confirme com o usuário, porque isso altera MRR e
indicadores. Datas no formato YYYY-MM-DD."

### 5.1 Leitura (`mcp:read` ou `mcp:write`)

| Ferramenta | Parâmetros | Implementação | Retorno |
|---|---|---|---|
| `contexto` | — | Consulta `Empresa`, a chave e as etapas ativas. | Empresa (id, nome), nome da chave, escopos, responsável padrão (id, nome), data de hoje, lista de pipelines. |
| `listar_cadastros` | — | Consulta direta, só registros ativos da empresa. | `etapas` (id, nome, ordem, pipeline, agrupadas por pipeline), `produtos`, `origens` (como conheceu), `motivos_perda`, `responsaveis` (usuários ativos da empresa). |
| `buscar_oportunidades` | `texto?`, `status?` (`ativo`\|`ganho`\|`perdido`\|`stand-by`), `etapa_id?`, `pipeline?`, `responsavel_id?`, `produto_id?`, `temperatura?` (`quente`\|`morno`\|`frio`), `ultimo_contato_de?`, `ultimo_contato_ate?`, `pagina=1`, `por_pagina=20` (máx. 50) | `oportunidade_service.list_oportunidades` com os filtros novos (seção 7). Só oportunidades com `opoAtivo=True`. | `{itens: [resumo], total, pagina, por_pagina}`. |
| `obter_oportunidade` | `oportunidade_id` | `get_oportunidade` + 10 históricos mais recentes. | Oportunidade completa (5.3) + `historico_recente` + `ciclo_anterior` (id, título, status) se existir + `url`. |
| `listar_historico` | `oportunidade_id`, `pagina=1`, `por_pagina=20` (máx. 50) | `oportunidade_historico_service.list_historicos`, do mais recente para o mais antigo. | `{itens: [{id, data, autor, conteudo}], total, pagina, por_pagina}`. |
| `resumo_funil` | `pipeline?` (padrão: pipeline da primeira etapa por ordem) | Agregação `GROUP BY opoEtkId` das oportunidades ativas (`opoAtivo` e `opoStatusFechamento IS NULL`) da empresa. | Por etapa, na ordem do kanban: `{etapa: {id, nome}, quantidade, valor_total}` + totais. Etapas vazias aparecem com zero. |
| `obter_indicadores` | `data_inicial?`, `data_final?`, `responsavel_id?`, `status?` (`todas`\|`ganhas`\|`perdidas`\|`ativas`), `incluir_serie_mensal=false`, `anos_serie?` (lista) | `crm_dashboard_service.get_dashboard` com `CrmDashboardFiltroParams`. | `cards`, `resumoMetas`, `temMeta`, `motivosPerda`, `rankings`; `serieMensal` só se pedido. `graficos` e `filtros` são omitidos. |
| `detalhar_indicador` | `metrica?` (`recebidas`\|`ganhas`\|`perdidas`\|`ativas`\|`mrrIncremental`\|`valorProjeto`), `periodo?` (`YYYY-MM`), `fonte?`, `solucao?`, `motivo_perda?`, `data_inicial?`, `data_final?`, `responsavel_id?` | `crm_dashboard_service.list_dashboard_oportunidades`, validando a métrica com `normalizar_metrica_drill`. | `{itens, total, resumo}` como o service devolve. O service limita a 100 itens; quando `total` > itens, a resposta traz `truncado: true`. |
| `obter_metas` | `ano` | `crm_meta_mensal_service.list_resumo_ano`. | Resumo mensal meta × realizado do ano. |

### 5.2 Escrita (`mcp:write`)

| Ferramenta | Parâmetros | Implementação | Regras |
|---|---|---|---|
| `criar_lead` | `nome?`, `empresa?`, `email?`, `telefone?`, `origem="mcp"`, `observacoes?`, `responsavel_email?`, `valor?` | Monta `LeadIntakeRequest` e chama `lead_intake_service.processar_lead(db, emp_id, ich_id, payload)`. | Mesmas validações da API (e-mail ou telefone obrigatório). `ConflictError` vira mensagem clara. Retorna `{status: created\|updated, oportunidade_id, deduplicado_por, ciclo_anterior_id, url}`. |
| `atualizar_oportunidade` | `oportunidade_id` + opcionais: `titulo`, `contato`, `empresa`, `email`, `telefone`, `solucao`, `produto_id`, `responsavel_id`, `origem_id`, `valor`, `receita_pontual`, `dores`, `comentarios`, `data_recebimento` | `oportunidade_service.update_oportunidade` com um `OportunidadeUpdate` contendo **só** os campos informados. | O esquema da ferramenta não tem campos de etapa, status, fechamento ou ativo. IDs de produto/responsável/origem são validados contra a empresa da chave. Sem nenhum campo → erro "Nenhum campo para atualizar". |
| `mover_etapa` | `oportunidade_id`, `etapa_id` | `oportunidade_service.mover_etapa`. | Validação de funil existente; histórico e webhook `deal.stage_changed` já disparam no service. |
| `atualizar_qualificacao` | `oportunidade_id` + opcionais: `temperatura` (`quente`\|`morno`\|`frio`), `lead_score` (0–10), `reuniao_confirmada`, `proposta_enviada` | Chama `set_temperatura`, `set_lead_score`, `set_reuniao_confirmada`, `set_proposta_enviada` só para os campos informados. | Pelo menos um campo. Retorna a oportunidade atualizada. |
| `registrar_interacao` | `oportunidade_id`, `conteudo` (1–10.000 caracteres) | `oportunidade_historico_service.create_historico(..., usu_id=usuResponsavelPadraoId)` com conteúdo prefixado `[via MCP · <nome da chave>] `. | O service grava com a data/hora atual e atualiza `opoDataUltimoContato` para hoje. |
| `marcar_ganho` | `oportunidade_id`, `data_fechamento`, `tipo` (`recorrencia`\|`projeto`), `valor_fechado` (> 0) | `set_oportunidade_status_fechamento(..., "ganho", data=OportunidadeGanharRequest(...))`, com `tipo` → `opoFechadoRecorrencia` 0/1. | Se já estiver ganha: não altera e responde "A oportunidade já está marcada como ganha". |
| `marcar_perdido` | `oportunidade_id`, `motivo_id`, `observacao?` | Valida oportunidade e motivo (ativo, da empresa) **antes de qualquer gravação**; depois grava `opoMcaId` via `update_oportunidade`, chama `set_oportunidade_status_fechamento(..., "perdido")` e, com `observacao`, registra uma interação (prefixada). | Cada service faz o próprio commit, então as gravações não são uma transação única; por isso toda validação vem antes. Se já estiver perdida: não altera e avisa. |
| `colocar_stand_by` | `oportunidade_id`, `data_retorno` (≥ hoje) | `set_oportunidade_stand_by` com `OportunidadeStandByRequest(opoDataUltimoContato=data_retorno)`. | Data no passado → erro. |
| `reativar_oportunidade` | `oportunidade_id` | `reativar_oportunidade_para_funil`. | Se já estiver ativa: não altera e avisa. |

Todas as ferramentas de escrita retornam a oportunidade atualizada no formato 5.3 (exceto
`registrar_interacao`, que retorna o registro de histórico criado).

Oportunidade inexistente, de outra empresa ou inativa → "Oportunidade não encontrada" (mesmo
texto nos três casos). Como `get_oportunidade` não filtra `opoAtivo`, o MCP carrega a
oportunidade por um helper próprio (`obter_oportunidade_ativa`) que aplica os três filtros,
e toda ferramenta que recebe `oportunidade_id` passa por ele antes de chamar o service.

### 5.3 Formato da oportunidade

```json
{
  "id": 123,
  "titulo": "...",
  "contato": "...", "empresa": "...", "email": "...", "telefone": "...",
  "solucao": "...",
  "status": "ativo | ganho | perdido | stand-by",
  "etapa": {"id": 4, "nome": "Proposta", "pipeline": "default"},
  "responsavel": {"id": 2, "nome": "..."},
  "produto": {"id": 1, "nome": "..."},
  "origem": {"id": 3, "nome": "..."},
  "motivo_perda": {"id": 5, "nome": "..."},
  "temperatura": "quente", "lead_score": 8,
  "reuniao_confirmada": true, "proposta_enviada": false,
  "valor": 12000.0, "receita_pontual": false,
  "data_recebimento": "2026-09-01", "data_ultimo_contato": "2026-09-20",
  "fechamento": {"data": "...", "tipo": "recorrencia | projeto", "valor": 0.0},
  "dores": "...", "comentarios": "...",
  "origem_externa": {"sistema": "...", "utm_source": "...", "utm_campaign": "..."},
  "criado_em": "...", "atualizado_em": "...",
  "url": "https://.../oportunidades/123"
}
```

- Relacionamentos nulos saem como `null`. `fechamento` só aparece quando ganha/perdida/stand-by.
- O **resumo** usado em listas traz: `id, titulo, contato, empresa, status, etapa, responsavel,
  temperatura, lead_score, valor, data_ultimo_contato`.
- Nomes de etapa/responsável/produto/origem/motivo são resolvidos em lote (uma consulta por
  tabela por chamada), nunca um por item.
- A `url` usa a mesma regra de `_url_da_oportunidade` do `lead_intake_router`, que passa a
  ficar num lugar compartilhado (`core/`) para os dois usarem.

## 6. Erros e log — decorador `@ferramenta(escrita: bool)`

Cada ferramenta é registrada como `@mcp.tool()` + `@ferramenta(escrita=...)`. O decorador:

1. Abre `abrir_sessao(ctx)` e checa o escopo (4.3).
2. Mede a duração e executa a função passando o `ContextoMCP`.
3. Traduz exceções para o erro de ferramenta do SDK (o Claude recebe `isError` com a mensagem):

| Exceção | Mensagem ao Claude | `status_http` / `resultado` no log |
|---|---|---|
| Sucesso | — | 200 / `ok` |
| `BadRequestError`, `ValueError` de validação própria | `detail` / mensagem | 400 / `bad_request` |
| Falta de escopo, `AuthorizationError` | `detail` | 403 / `forbidden` |
| `NotFoundError` | `detail` | 404 / `not_found` |
| `ConflictError` | `detail` | 409 / `conflict` |
| Outra `HTTPException` | `detail` | `status_code` / `error` |
| Qualquer outra exceção | "Erro interno ao executar a ferramenta." | 500 / `error` (traceback só no `logger.exception`) |

Parâmetros fora do esquema (tipo errado, enum inválido, limites) são rejeitados pelo SDK antes
de chegar ao decorador.

4. Faz `rollback` em qualquer exceção. Isso só desfaz o que ainda não foi commitado: os services
   de escrita fazem commit próprio, por isso as ferramentas validam tudo antes de chamar o
   primeiro service que grava.
5. Registra `integracao_log_service.registrar(db, rota="mcp:<ferramenta>", metodo="TOOL",
   status_http, resultado, emp_id, ich_id, opo_id=<oportunidade_id quando houver>,
   payload=<argumentos>, erro=<{"detalhe": ...} em falha>, duracao_ms)`. O `registrar` já
   aplica `redigir_payload` e tem commit próprio.

## 7. Mudanças em código existente

1. **`oportunidade_service.list_oportunidades`** ganha parâmetros opcionais, todos com padrão
   que mantém o comportamento atual:
   - `busca: str | None` — `ILIKE` em título, nome do contato, empresa do contato e e-mail.
   - `temperatura: str | None`.
   O parâmetro `titulo` continua funcionando como hoje.
2. **`_url_da_oportunidade`** sai de `lead_intake_router.py` para `backend/core/links.py`
   (`url_da_oportunidade`), e o router passa a importá-la.
3. **`main.py`**: mount e lifespan (3.2).
4. **`requirements.txt`**: `mcp==2.0.0`.

Nenhuma migração de banco. No frontend, a única mudança é de texto: a tela de chaves já lista os escopos
a partir de `ESCOPOS_CONHECIDOS`, que já inclui `mcp:read` e `mcp:write`. Só o texto de ajuda
da tela ganha uma linha explicando que o MCP usa esses escopos.

## 8. Testes

Padrão do projeto: `unittest` + `unittest.mock`, sem banco real.

| Arquivo | Cobre |
|---|---|
| `tests/test_mcp_autenticacao.py` | Extração da chave do caminho (com e sem `root_path`, atrás do prefixo do nginx); header `X-API-Key`; 401 para chave ausente, inválida e sem escopo `mcp:*`; remoção de headers `x-sdcrm-*` vindos de fora; log `unauthorized` só com prefixo. |
| `tests/test_mcp_ferramenta.py` | Tradução de cada exceção da tabela da seção 6; rollback; chamada ao log com rota, resultado e `opo_id`; chave só `mcp:read` barrada em escrita; chave revogada entre chamadas barrada. |
| `tests/test_mcp_ferramentas.py` | Cada ferramenta chama o service certo com `company_id` da chave; `marcar_perdido` grava motivo + status + interação opcional; status repetido não altera; `atualizar_oportunidade` sem campos → erro; `colocar_stand_by` com data passada → erro; `registrar_interacao` usa o prefixo e o responsável padrão. |
| `tests/test_mcp_serializacao.py` | Formato 5.3, resumo de lista, `fechamento` condicional, resolução de nomes em lote. |
| `tests/test_mcp_protocolo.py` | Cliente MCP em memória do SDK: `initialize` → `list_tools` (18 ferramentas, nomes e esquemas) → `call_tool` com `abrir_sessao` e services simulados. |
| `tests/test_oportunidade_busca.py` | `list_oportunidades` com `busca` e `temperatura`, e sem eles gerando a mesma consulta de antes. |

### Validação manual (obrigatória antes de dar como pronto)

1. Subir o backend local; criar uma chave com `mcp:read` + `mcp:write`.
2. `claude mcp add --transport http sdcrm http://localhost:8000/api/mcp/<chave>`.
3. Roteiro: `contexto` → `listar_cadastros` → `buscar_oportunidades` → `obter_oportunidade` →
   `registrar_interacao` → `mover_etapa` → `obter_indicadores`. Conferir no CRM (histórico,
   etapa) e na tela de logs de integração.
4. Criar uma chave só com `mcp:read` e confirmar que `mover_etapa` é recusada.
5. Revogar a chave e confirmar que a chamada seguinte falha.

## 9. Documentação

Nova seção "Servidor MCP" em `docs/INTEGRACAO_API.md`:

- Como gerar a chave e quais escopos marcar.
- URL do conector: `https://<host>/crm/api/mcp/<chave>`.
- Como conectar no claude.ai (conector personalizado), no Claude Code (`claude mcp add
  --transport http ...`) e no n8n (nó MCP Client com header `X-API-Key`).
- Lista das ferramentas com uma linha cada.
- Alerta sobre a chave na URL e recomendação de chave exclusiva.
