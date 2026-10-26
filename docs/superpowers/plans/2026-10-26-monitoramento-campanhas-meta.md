# Monitoramento de Campanhas Meta — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levar o Meta Ads do CRM do nível campanha para o nível anúncio, com o ID do anúncio em cada lead, funil por criativo (lead → MQL → oportunidade → contrato), resumo diário com leitura por IA, seis alertas configuráveis e ferramentas no MCP — tudo dentro do CRM, só leitura na Meta.

**Architecture:** Estende o pacote `backend/services/meta_ads/` da fase 1 com módulos novos de responsabilidade única (`rastreio`, `funil`, `config_monitor`, `alertas`, `resumo`) e um registro estruturado de mudança de estágio em `services/etapa_historico.py`. A sync diária ganha os níveis conjunto e anúncio; o worker ganha um ciclo de hora em hora para alertas e resumo. O fluxo n8n troca o INSERT direto no banco pela API de leads, e uma carga retroativa liga os leads antigos aos anúncios.

**Tech Stack:** Python 3.11/3.14, FastAPI 0.135.2, SQLAlchemy 2.0.48, Alembic 1.13.2, httpx 0.28.1, `unittest` + SQLite em memória (`backend/tests/banco_sqlite.py`), IA via `services/llm/llm_factory.get_scope_provider().chat_completion`; React 18 + TS + Vite; n8n (MCP).

**Spec:** `docs/superpowers/specs/2026-10-26-monitoramento-campanhas-meta-design.md` (base: `docs/superpowers/specs/2026-10-14-meta-ads-campanhas-design.md`)

## Global Constraints

- Nenhuma escrita na Meta, em nenhuma circunstância. Token só no cabeçalho `Authorization`, nunca em URL, log ou resposta.
- Toda consulta e gravação filtra pela empresa (`X-Company-Id` ou chave de integração). Rotas de configuração exigem `require_admin`; leitura exige só `require_user_in_company`.
- Dados pessoais de lead (nome, telefone, e-mail) **só** no alerta "lead sem contato" e na lista "Origem Anúncios sem registro na Meta". Nunca no resumo, na leitura por IA ou nas ferramentas MCP.
- MQL = primeira chegada ao estágio configurado (padrão "Reunião de Levantamento") ou a estágio do mesmo pipeline com ordem **maior**; estágios com a **mesma** ordem (ex.: "Pré Reunião") não contam; ganho sem passagem = data de fechamento. Oportunidade = mesma regra com o estágio "Reunião de Vendas". Contrato = `opoStatusFechamento = 'ganho'`, data `opoDataFechamento`. Voltar de estágio não desfaz.
- Atribuição ao **primeiro anúncio**: `opoMeta*` e `opoManId` só são preenchidos quando vazios.
- CPL principal = investimento ÷ leads **Meta**; "Custo por lead CRM" = investimento ÷ leads CRM, coluna separada. Custo por MQL/oportunidade e CAC usam contagens do CRM.
- Funil conta por evento no período (cada etapa pela própria data).
- Limites iniciais: CPL > **1,5×** média dos 7 dias anteriores; gasto ≥ **R$ 150** em 7 dias sem lead; frequência 7 dias > **3**; CTR **30%** abaixo da primeira semana (anúncio com 14+ dias e 1.000+ impressões em cada janela); lead sem contato > **24 h**; gasto mínimo para o ranking do resumo **R$ 50**; resumo às **8h** (America/Sao_Paulo), segunda a sexta; segunda cobre **sexta a domingo**.
- Prefixos da Meta removidos: `l:`, `c:`, `as:`, `ag:`, `p:`.
- Mensagens e textos em português. Padrão de nomes `<alias><Campo>` (`docs/DATABASE_GUIDELINES.md`).
- Testes: `.venv/Scripts/python -m unittest backend.tests.<modulo> -v` da raiz; suíte completa: `.venv/Scripts/python -m unittest $(ls backend/tests/test_*.py | sed 's#/#.#g; s#\.py$##' | tr '\n' ' ')`. Frontend: `npx tsc --noEmit -p .` em `frontend/` com exatamente **6** erros (pré-existentes) e `npm run build` OK.
- **Nunca** rodar `alembic upgrade`, alterar/publicar fluxos n8n, criar chaves de integração no banco real ou rodar cargas retroativas sem ok explícito do Carlos no momento. Essas ações ficam na Task 16, executada pelo controlador.
- Nunca `git add -A`: o working tree tem alterações não relacionadas (`.venv/`, `__pycache__/`, `frontend/dist/`).

## Review Focus

1. **Lead que reenvia o formulário por outro anúncio** — o crédito fica com o primeiro anúncio e o reenvio vira só uma nota no histórico (teste na Task 5: `test_reenvio_por_outro_anuncio_mantem_primeiro`).
2. **Carga retroativa com várias linhas da planilha para o mesmo lead** — a mais antiga vence, rodar duas vezes não muda nada (teste na Task 6: `test_linhas_repetidas_primeira_vence_e_idempotente`).
3. **"Pré Reunião" (mesma ordem da Reunião de Levantamento) não vira MQL** (teste na Task 8: `test_estagio_de_mesma_ordem_nao_conta`).
4. **Primeira execução do "lead sem contato"** — leads anteriores à data em que o alerta foi ligado não disparam (teste na Task 12: `test_lead_sem_contato_ignora_backlog`).
5. **Mesmo problema avaliado em dias seguidos** — o alerta é atualizado, não duplicado; some quando a condição para de valer (teste na Task 12: `test_alerta_nao_duplica_e_resolve`).

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `backend/services/meta_ads/cliente_graph.py` | Modificar | Permissões, conjuntos, anúncios, insights por anúncio, frequência 7d, status da conta |
| `backend/models/meta_ads_conjunto.py`, `meta_ads_anuncio.py`, `meta_ads_insight_anuncio_diario.py` | Criar | Dados por conjunto e anúncio |
| `backend/models/oportunidade_etapa_historico.py` | Criar | Transições de estágio |
| `backend/models/meta_ads_monitor_config.py`, `meta_ads_alerta.py`, `meta_ads_resumo.py` | Criar | Config, alertas, resumos |
| `backend/models/meta_ads_conta.py`, `oportunidade.py` | Modificar | Colunas novas |
| `backend/alembic/versions/0031_meta_ads_anuncios.py` … `0036_meta_ads_resumo.py` | Criar | Uma migration por task que cria tabela |
| `backend/services/meta_ads/sincronizacao.py` | Modificar | Gravar conjuntos/anúncios/insights por anúncio, status da conta, checagem de permissão |
| `backend/services/meta_ads/rastreio.py` | Criar | Limpeza de prefixos, aplicar ids Meta (primeiro anúncio), sinal de Meta, carga retroativa |
| `backend/services/meta_ads/vinculo.py` | Modificar | Resolver anúncio → campanha |
| `backend/services/etapa_historico.py` | Criar | `registrar_transicao`, carga retroativa a partir do texto do histórico |
| `backend/services/meta_ads/config_monitor.py` | Criar | Config por empresa com padrões |
| `backend/services/meta_ads/funil.py` | Criar | Datas de MQL/oportunidade, interação humana, contagens do funil |
| `backend/services/meta_ads/indicadores.py` | Modificar | Árvore campanha→conjunto→anúncio, CPL Meta, regra "lead da Meta" por conta, revisão de origem |
| `backend/services/meta_ads/alertas.py` | Criar | Regras puras + avaliação + persistência |
| `backend/services/meta_ads/resumo.py` | Criar | Período de referência, ranking, payload, leitura IA, persistência |
| `backend/workers/meta_ads_worker.py` | Modificar | Ciclo de hora em hora; alertas diários após a sync |
| `backend/schemas/lead_integracao.py`, `backend/services/lead_intake_service.py`, `backend/routers/lead_intake_router.py` | Modificar | Campos Meta na API; endpoint de rastreio |
| `backend/services/oportunidade_service.py` | Modificar | Chamar `registrar_transicao` |
| `backend/schemas/meta_ads.py`, `backend/routers/meta_ads_router.py` | Modificar | Schemas e rotas novas |
| `backend/mcp_crm/ferramentas/campanhas.py`, `__init__.py` | Criar/Modificar | Ferramentas MCP |
| `backend/scripts/carga_etapas.py` | Criar | CLI da carga retroativa de estágios |
| `frontend/src/pages/Campanhas/*` | Modificar | Árvore, colunas novas, cobertura, revisão de origem |
| `frontend/src/pages/Monitoramento/MonitoramentoPage.tsx`, `ConfigMonitoramentoModal.tsx` | Criar | Resumo, alertas, configuração |
| `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx` | Modificar | Rota/menu/cabeçalho `/monitoramento` |
| `docs/META_ADS.md` | Modificar | Monitoramento, n8n, carga retroativa |

---

### Task 1: Token só leitura

**Files:**
- Modify: `backend/services/meta_ads/cliente_graph.py`, `backend/services/meta_ads/contas.py` (`testar_conta`), `backend/services/meta_ads/sincronizacao.py` (`sincronizar_conta`, `contas_da_rodada_diaria`), `backend/models/meta_ads_conta.py` (constante)
- Test: `backend/tests/test_meta_ads_cliente_graph.py`, `backend/tests/test_meta_ads_contas.py`, `backend/tests/test_meta_ads_sincronizacao.py`

**Interfaces:**
- Produces: `cliente_graph.permissoes_de_escrita(permissoes: set[str]) -> set[str]`; `ClienteGraph.listar_permissoes() -> set[str]` (`GET /me/permissions`, só `status == "granted"`); `class PermissaoExcessivaErro(MetaGraphErro)`; constante `STATUS_PERMISSAO_EXCESSIVA = "permissao_excessiva"` em `models/meta_ads_conta.py`; mensagem fixa `MENSAGEM_PERMISSAO_EXCESSIVA = "Token com permissão de escrita — gere um token só leitura (ads_read)."` em `cliente_graph.py`.

- [ ] **Step 1: Testes que falham**

```python
# test_meta_ads_cliente_graph.py
class PermissoesTests(unittest.TestCase):
    def test_so_leitura_passa(self):
        self.assertEqual(g.permissoes_de_escrita({"ads_read", "read_insights"}), set())
    def test_escrita_detectada(self):
        self.assertEqual(
            g.permissoes_de_escrita({"ads_read", "ads_management", "pages_manage_ads", "publish_video", "business_management"}),
            {"ads_management", "pages_manage_ads", "publish_video", "business_management"},
        )
    def test_listar_permissoes_so_granted(self):
        corpo = {"data": [{"permission": "ads_read", "status": "granted"}, {"permission": "ads_management", "status": "declined"}]}
        cliente, feitas, _ = _cliente([(200, corpo)])
        with cliente:
            self.assertEqual(cliente.listar_permissoes(), {"ads_read"})
        self.assertIn("/me/permissions", str(feitas[0].url))
```
```python
# test_meta_ads_contas.py — FabricaFalsa ganha `permissoes` (padrão {"ads_read"}) e método listar_permissoes
    def test_testar_recusa_token_com_escrita(self):
        resp = self._criar()
        fab = FabricaFalsa(conta=g.ContaMeta("X", "BRL", "America/Sao_Paulo"), permissoes={"ads_read", "ads_management"})
        r = contas.testar_conta(self.db, self.emp.empId, resp.macId, fabrica_cliente=fab)
        self.assertFalse(r.ok)
        self.assertEqual(r.mensagem, g.MENSAGEM_PERMISSAO_EXCESSIVA)
```
```python
# test_meta_ads_sincronizacao.py — ClienteFalso ganha `permissoes` (padrão {"ads_read"}) e listar_permissoes
    def test_permissao_de_escrita_bloqueia_sync(self):
        cliente = ClienteFalso([g.CampanhaMeta("1", "A", None, "ACTIVE")], permissoes={"ads_management"})
        r = self._sync(cliente, inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual(r.status, STATUS_PERMISSAO_EXCESSIVA)
        self.assertEqual(cliente.periodos, [])          # nada foi buscado
        self.assertEqual(s.contas_da_rodada_diaria(self.db), [])
```

- [ ] **Step 2: Rodar e ver falhar** — `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_cliente_graph backend.tests.test_meta_ads_contas backend.tests.test_meta_ads_sincronizacao -v` → falhas por nomes inexistentes.

- [ ] **Step 3: Implementar.** Escrita = permissão em `{"ads_management", "business_management", "catalog_management"}` **ou** que contenha `"manage"` **ou** comece com `"publish"`. `testar_conta` chama `listar_permissoes()` antes de `obter_conta` e devolve `ok=False, mensagem=MENSAGEM_PERMISSAO_EXCESSIVA` sem gravar nada. `sincronizar_conta` chama `listar_permissoes()` logo após abrir o cliente; se houver escrita, levanta `PermissaoExcessivaErro(MENSAGEM_PERMISSAO_EXCESSIVA)`, tratada como status `STATUS_PERMISSAO_EXCESSIVA` (log com status `erro`). `contas_da_rodada_diaria` exclui `STATUS_TOKEN_INVALIDO` **e** `STATUS_PERMISSAO_EXCESSIVA`. Trocar o token (PUT) volta para `pendente` como hoje. Atualizar os fakes existentes (`ClienteFalso`, `FabricaFalsa`) para aceitar `permissoes`.

- [ ] **Step 4: Rodar e ver passar** — mesmo comando → OK.

- [ ] **Step 5: Commit** — `git add` dos arquivos listados; mensagem `Meta Ads: recusa token com permissão de escrita`.

---

### Task 2: Cliente da Graph — conjuntos, anúncios e métricas por anúncio

**Files:**
- Modify: `backend/services/meta_ads/cliente_graph.py`
- Test: `backend/tests/test_meta_ads_cliente_graph.py`

**Interfaces:**
- Produces (dataclasses frozen):
  - `ConjuntoMeta(id: str, nome: str, campanha_id: str, status: str | None)`
  - `AnuncioMeta(id: str, nome: str, conjunto_id: str, campanha_id: str, status: str | None, motivo: str | None, criado_em: date | None)`
  - `InsightAnuncioDia(anuncio_id: str, anuncio_nome: str, conjunto_id: str, campanha_id: str, dia: date, investimento: Decimal, impressoes: int, alcance: int, cliques: int, cliques_link: int, leads: int)`
  - `FrequenciaAnuncio(anuncio_id: str, impressoes: int, alcance: int, frequencia: float)`
  - `StatusConta(account_status: int | None, disable_reason: int | None)`
- Métodos de `ClienteGraph`: `listar_conjuntos(act) -> list[ConjuntoMeta]` (`/{act}/adsets`, fields `id,name,campaign_id,effective_status`), `listar_anuncios(act) -> list[AnuncioMeta]` (`/{act}/ads`, fields `id,name,adset_id,campaign_id,effective_status,created_time,issues_info,ad_review_feedback`), `listar_insights_anuncios(act, inicio, fim) -> list[InsightAnuncioDia]` (`level=ad`, `time_increment=1`, fields `ad_id,ad_name,adset_id,campaign_id,spend,impressions,reach,clicks,inline_link_clicks,actions`), `frequencia_7_dias(act, inicio, fim) -> list[FrequenciaAnuncio]` (`level=ad`, sem `time_increment`, fields `ad_id,impressions,reach,frequency`), `obter_status_conta(act) -> StatusConta` (fields `account_status,disable_reason`). Todos com `limit=500` e paginação via `_paginar`.

- [ ] **Step 1: Testes que falham** — um teste por método com `httpx.MockTransport`:
  - `test_listar_anuncios_extrai_motivo`: `issues_info=[{"error_summary": "Anúncio reprovado"}]` → `motivo == "Anúncio reprovado"`; sem `issues_info` mas `ad_review_feedback={"global": {"POLICY": "Texto"}}` → `motivo == "Texto"`; `created_time="2026-09-10T12:00:00-0300"` → `criado_em == date(2026, 9, 10)`.
  - `test_insights_anuncio_converte`: linha com `spend "12.30"`, `impressions "1000"`, `reach "800"`, `clicks "40"`, `inline_link_clicks "25"`, `actions [{"action_type":"lead","value":"2"}]` → valores tipados iguais; params `level == "ad"` e `time_increment == "1"`.
  - `test_frequencia_sem_time_increment`: `"time_increment" not in feitas[0].url.params`; `frequency "3.4"` → `3.4`.
  - `test_status_conta`: `{"account_status": 3, "disable_reason": 0}` → `StatusConta(3, 0)`.
  - `test_conjuntos_paginam`: duas páginas → dois itens.

- [ ] **Step 2: Rodar e ver falhar** — `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_cliente_graph -v`.

- [ ] **Step 3: Implementar** os métodos e dataclasses acima reaproveitando `_paginar`, `_inteiro` e `extrair_leads`. `motivo`: primeiro `error_summary`/`error_message` de `issues_info`, senão o primeiro valor de `ad_review_feedback["global"]`, senão `None`; cortar em 300 caracteres.

- [ ] **Step 4: Rodar e ver passar.**

- [ ] **Step 5: Commit** — `Meta Ads: cliente lê conjuntos, anúncios e métricas por anúncio`.

---

### Task 3: Tabelas por anúncio e sync estendida

**Files:**
- Create: `backend/models/meta_ads_conjunto.py` (alias `mcj`), `backend/models/meta_ads_anuncio.py` (`man`), `backend/models/meta_ads_insight_anuncio_diario.py` (`mia`), `backend/alembic/versions/0031_meta_ads_anuncios.py` (down_revision `0030_meta_ads`)
- Modify: `backend/models/meta_ads_conta.py` (`macAccountStatus: int | None`, `macDisableReason: int | None`), `backend/models/__init__.py`, `backend/services/meta_ads/sincronizacao.py`, `backend/tests/banco_sqlite.py` (fábricas `criar_conjunto(db, campanha, externa, nome, status="ACTIVE")`, `criar_anuncio(db, conjunto, externa, nome, status="ACTIVE", criado_em=None)`, `criar_insight_anuncio(db, anuncio, dia, investimento, *, impressoes=1000, alcance=800, cliques=50, cliques_link=30, leads=0)`)
- Test: `backend/tests/test_meta_ads_modelos.py`, `backend/tests/test_meta_ads_sincronizacao.py`

**Interfaces:**
- Consumes: Task 2 dataclasses e métodos.
- Produces:
  - `MetaAdsConjunto`: `mcjId, mcjEmpId, mcjMacId, mcjMcgId (FK campanha, CASCADE), mcjConjuntoExterno (String 40), mcjNome (400), mcjStatus (30)`, auditoria; único `(mcjMacId, mcjConjuntoExterno)`.
  - `MetaAdsAnuncio`: `manId, manEmpId, manMacId, manMcgId, manMcjId (FK conjunto, CASCADE), manAnuncioExterno (40), manNome (400), manStatus (30), manMotivo (String 300), manCriadoEmMeta (Date), manPrimeiroDia (Date — menor dia com impressão > 0 já visto)`, auditoria; único `(manMacId, manAnuncioExterno)`; índice `(manEmpId, manAnuncioExterno)`.
  - `MetaAdsInsightAnuncioDiario`: `miaId, miaEmpId, miaMacId, miaManId (CASCADE), miaData, miaInvestimento Numeric(14,2), miaImpressoes, miaAlcance, miaCliques, miaCliquesLink, miaLeadsMeta`; único `(miaManId, miaData)`; índice `(miaEmpId, miaData)`.
  - Na sync: dentro da mesma transação de `_gravar`, upsert de conjuntos e anúncios (anúncio/conjunto que só aparece no insight é criado com o nome do insight), DELETE+INSERT de `meta_ads_insight_anuncio_diario` da conta no período, `manPrimeiroDia = min(manPrimeiroDia, menor dia com impressão)`, e `macAccountStatus/macDisableReason` de `obter_status_conta`. As chamadas HTTP novas acontecem antes do `db.rollback()` que já encerra a leitura (fase 1, correção I1).

- [ ] **Step 1: Testes que falham**
  - `test_meta_ads_modelos`: `test_anuncio_duplicado_na_conta_recusado`, `test_insight_anuncio_duplicado_no_dia_recusado`.
  - `test_meta_ads_sincronizacao` (`ClienteFalso` ganha `conjuntos`, `anuncios`, `insights_anuncio`, `status_conta`):
    - `test_grava_conjuntos_anuncios_e_insights_por_anuncio`: 1 campanha, 1 conjunto, 2 anúncios, 3 linhas de insight → 1 `MetaAdsConjunto`, 2 `MetaAdsAnuncio` ligados à campanha e ao conjunto, 3 `MetaAdsInsightAnuncioDiario`.
    - `test_anuncio_so_no_insight_e_criado`.
    - `test_regrava_insights_anuncio_sem_sobras` (mesmo padrão do teste de campanha).
    - `test_primeiro_dia_e_menor_dia_com_impressao`: insights em 05/10 (0 impressões) e 06/10 (100) → `manPrimeiroDia == date(2026,10,6)`; nova sync com 03/10 (50) → `date(2026,10,3)`.
    - `test_grava_status_da_conta`: `StatusConta(3, 0)` → `macAccountStatus == 3`.
    - `test_erro_no_nivel_anuncio_nao_grava_nada`: `listar_insights_anuncios` levanta `MetaGraphErro` → nenhum insight de campanha novo gravado e status `erro`.

- [ ] **Step 2: Rodar e ver falhar.**

- [ ] **Step 3: Implementar** models, migration (idempotente no estilo da `0030`; índice de FK criado **antes** da FK), registro em `models/__init__.py`, fábricas e a extensão de `_gravar` (extrair helpers `_gravar_conjuntos_e_anuncios(...)` e `_gravar_insights_anuncio(...)` para não inchar `_gravar`).

- [ ] **Step 4: Rodar e ver passar** + suíte completa.

- [ ] **Step 5: Commit** — `Meta Ads: conjuntos, anúncios e métricas diárias por anúncio`.

---

### Task 4: Registro estruturado de mudança de estágio

**Files:**
- Create: `backend/models/oportunidade_etapa_historico.py` (alias `oeh`), `backend/alembic/versions/0032_etapa_historico.py` (down `0031_meta_ads_anuncios`), `backend/services/etapa_historico.py`, `backend/scripts/carga_etapas.py`
- Modify: `backend/services/oportunidade_service.py` (`create_oportunidade`, `update_oportunidade`, `mover_etapa`), `backend/services/lead_intake_service.py` (`_criar`), `backend/mcp_crm/ferramentas/funil.py` (passa `origem="mcp"` ao chamar `mover_etapa`), `backend/models/__init__.py`
- Test: `backend/tests/test_etapa_historico.py`

**Interfaces:**
- Produces:
  - `OportunidadeEtapaHistorico`: `oehId, oehEmpId, oehOpoId (FK CASCADE), oehEtkIdDe (nullable, FK SET NULL), oehEtkIdPara (FK SET NULL, nullable), oehData (DateTime tz), oehOrigem (String 20: ui|api|mcp|retroativo)`; índice `(oehOpoId, oehData)`, `(oehEmpId, oehData)`.
  - `etapa_historico.registrar_transicao(db, opo: Oportunidade, etk_de: int | None, etk_para: int | None, origem: str, quando: datetime | None = None) -> None` — não faz commit; ignora quando `etk_de == etk_para`.
  - `etapa_historico.REGEX_TRANSICAO` casando `Etapa alterada de "X" para "Y".`
  - `etapa_historico.carga_retroativa(db, emp_id: int, *, aplicar: bool) -> dict` — devolve `{"transicoes": n, "criacoes": n, "nao_casadas": n}`; só grava se `aplicar=True`; idempotente (não duplica transição com mesma oportunidade, destino e data; se a oportunidade já tem qualquer linha `retroativo`, pula).
  - CLI: `.venv/Scripts/python -m backend.scripts.carga_etapas --empresa 2 [--aplicar]` (sem `--aplicar` = simulação, imprime o dict).
- Origem por caminho: `create_oportunidade`/`update_oportunidade`/`mover_etapa` → `"ui"` (o MCP chama `mover_etapa`; o parâmetro `origem` passa a ser opcional nessas funções com padrão `"ui"` e o MCP passa `"mcp"`); `lead_intake_service._criar` → `"api"`. Criação grava `de=None → para=estágio inicial`.

- [ ] **Step 1: Testes que falham** (SQLite):
  - `test_mover_etapa_grava_transicao`: mover 9→10 → uma linha `(9, 10, "ui")`.
  - `test_mesma_etapa_nao_grava`.
  - `test_criacao_grava_estagio_inicial`: `create_oportunidade` com etapa 9 → linha `(None, 9)`.
  - `test_update_com_troca_de_etapa_grava`.
  - `test_carga_retroativa_le_texto_do_historico`: histórico com `Etapa alterada de "Contatos" para "Reunião de Levantamento".` em 10/10 14:00 → transição `(id Contatos, id Levantamento, data 10/10 14:00, "retroativo")` + criação na `opoDataCriacao`.
  - `test_carga_retroativa_nome_desconhecido_conta_nao_casada`.
  - `test_carga_retroativa_idempotente`: aplicar duas vezes → mesma contagem de linhas.
  - `test_simulacao_nao_grava`.

- [ ] **Step 2: Rodar e ver falhar** — `.venv/Scripts/python -m unittest backend.tests.test_etapa_historico -v`.

- [ ] **Step 3: Implementar.** Casamento de nome pelo `etkNome` normalizado (strip, minúsculas) dentro da empresa; se dois estágios tiverem o mesmo nome, preferir o do pipeline do estágio atual da oportunidade.

- [ ] **Step 4: Rodar e ver passar** + `backend.tests.test_lead_dedup backend.tests.test_mcp_ferramentas_escrita`.

- [ ] **Step 5: Commit** — `Funil: registro estruturado de mudança de estágio e carga retroativa`.

---

### Task 5: IDs da Meta no lead (API de leads e vínculo por anúncio)

**Files:**
- Create: `backend/services/meta_ads/rastreio.py`, `backend/alembic/versions/0033_rastreio_meta.py` (down `0032_etapa_historico`)
- Modify: `backend/models/oportunidade.py` (`opoMetaLeadId` String 40, `opoMetaCampanhaId` 40, `opoMetaConjuntoId` 40, `opoMetaAnuncioId` 40 com índice, `opoManId` FK `meta_ads_anuncio.manId` SET NULL com índice), `backend/models/meta_ads_conta.py` (`macExigirRastreio: bool` default False), `backend/schemas/lead_integracao.py` (`meta_lead_id`, `campaign_id`, `adset_id`, `ad_id`: `Optional[str]`, max 60), `backend/services/lead_intake_service.py` (`_criar`, `_atualizar`), `backend/services/meta_ads/vinculo.py`, `backend/schemas/oportunidade.py` (resposta: os quatro `opoMeta*` e `opoManId`)
- Test: `backend/tests/test_meta_ads_rastreio.py`, `backend/tests/test_meta_ads_vinculo.py`

**Interfaces:**
- Produces (em `rastreio.py`):
  - `limpar_id_meta(valor: str | None) -> str | None` — remove `l:`, `c:`, `as:`, `ag:`, `p:` do início e espaços; vazio → `None`.
  - `aplicar_ids_meta(db, opo, *, meta_lead_id, campaign_id, adset_id, ad_id) -> bool` — **primeiro anúncio**: preenche cada `opoMeta*` só se vazio; se o lead já tinha `opoMetaAnuncioId` diferente do novo, grava nota no histórico `Novo envio pelo anúncio <ad_id> (crédito mantido no primeiro anúncio).` e devolve `False`; não faz commit.
  - `tem_sinal_meta` — expressão SQLAlchemy: `or_(opoMetaLeadId.isnot(None), opoMetaAnuncioId.isnot(None), opoMcgId.isnot(None))`.
- Em `vinculo.py`: `vincular_oportunidade` e `vincular_pendentes` passam a resolver primeiro por `opoMetaAnuncioId` → `MetaAdsAnuncio` da empresa (preenche `opoManId` e, se `opoMcgId` vazio e não manual, `opoMcgId = anuncio.manMcgId`); só depois a regra por nome/UTM da fase 1. A escrita em lote continua com UPDATE guardado (`opoManId IS NULL` / `opoMcgId IS NULL AND opoMcgManual = false`).
- Na entrada de leads: `_criar` e `_atualizar` chamam `aplicar_ids_meta` com os campos limpos antes do `_vincular_campanha_meta`. Os campos Meta **não** entram em `aplicar_merge` (que sobrescreve UTMs).

- [ ] **Step 1: Testes que falham**
  - `test_limpar_id_meta`: `"ag:120250133121060008"` → `"120250133121060008"`; `"l:1645"` → `"1645"`; `"p:+5575988666626"` → `"+5575988666626"`; `"  "` → `None`; `"120"` → `"120"`.
  - `test_aplica_ids_no_lead_novo`.
  - `test_reenvio_por_outro_anuncio_mantem_primeiro`: lead com `ad_id` A recebe envio com B → `opoMetaAnuncioId == A`, retorno `False`, uma nota no histórico contendo `B`.
  - `test_api_de_leads_grava_ids_e_resolve_anuncio` (chama `lead_intake_service._criar` via helper de teste sem `GET_LOCK`, ou `_processar_com_lock` diretamente): payload com `ad_id="ag:999"` e anúncio `999` sincronizado → `opoMetaAnuncioId == "999"`, `opoManId == anuncio.manId`, `opoMcgId == anuncio.manMcgId`.
  - `test_vincular_pendentes_resolve_por_anuncio` (em `test_meta_ads_vinculo`).
  - `test_manual_nao_e_sobrescrito_pelo_anuncio`.

- [ ] **Step 2: Rodar e ver falhar.**

- [ ] **Step 3: Implementar** colunas, migration (índice antes de FK), schema, `rastreio.py`, ajustes no intake e no vínculo.

- [ ] **Step 4: Rodar e ver passar** + `test_lead_dedup`, `test_lead_normalizacao`, `test_mcp_ferramentas_escrita`, suíte completa.

- [ ] **Step 5: Commit** — `Meta Ads: ids de campanha, conjunto e anúncio no lead`.

---

### Task 6: Endpoint da carga retroativa de rastreio

**Files:**
- Modify: `backend/services/meta_ads/rastreio.py`, `backend/routers/lead_intake_router.py`, `backend/schemas/lead_integracao.py`
- Test: `backend/tests/test_meta_ads_rastreio.py`

**Interfaces:**
- Produces:
  - Schemas: `RastreioMetaItem(meta_lead_id: str, created_time: datetime, campaign_id: str | None, adset_id: str | None, ad_id: str | None, phone: str | None, email: str | None)`; `RastreioMetaRequest(itens: list[RastreioMetaItem], max 500)`; `RastreioMetaResponse(casados: int, nao_casados: int, ambiguos: int, ja_atribuidos: int)`.
  - `rastreio.aplicar_rastreio_retroativo(db, emp_id: int, itens: list[RastreioMetaItem]) -> RastreioMetaResponse` — processa por `created_time` crescente; casa por `opoMetaLeadId` (ou `opoOrigemExternalId`) = id limpo, depois telefone normalizado (`lead_normalizacao.normalizar_telefone` + `variantes_telefone`), depois e-mail normalizado; só oportunidades da empresa e ativas; mais de uma oportunidade casada → `ambiguos` e não grava; oportunidade que já tem `opoMetaAnuncioId` → `ja_atribuidos` (não muda); senão `aplicar_ids_meta` e `casados`. Ao fim, `vinculo.vincular_pendentes(db, emp_id)` e commit único.
  - Rota `POST /api/v1/leads/rastreio-meta` (`exigir_escopo(ctx, "leads:write")`, empresa da chave, log de requisição como em `/leads`). **Nunca cria lead.**

- [ ] **Step 1: Testes que falham**
  - `test_casa_por_lead_id_depois_telefone_depois_email` (três leads, três itens, cada um casando por um critério).
  - `test_sem_casamento_conta_nao_casado_e_nao_cria`: total de oportunidades inalterado.
  - `test_telefone_de_dois_leads_e_ambiguo`.
  - `test_linhas_repetidas_primeira_vence_e_idempotente`: dois itens do mesmo telefone, anúncios A (01/10) e B (05/10), enviados fora de ordem → lead com A; rodar de novo → `casados == 0`, `ja_atribuidos == 2` e nada mudou.
  - `test_outra_empresa_nao_e_tocada`.

- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar** + suíte completa.
- [ ] **Step 5: Commit** — `Meta Ads: carga retroativa de rastreio pela API`.

---

### Task 7: Configuração do monitoramento

**Files:**
- Create: `backend/models/meta_ads_monitor_config.py` (alias `mmc`), `backend/alembic/versions/0034_monitor_config.py` (down `0033_rastreio_meta`), `backend/services/meta_ads/config_monitor.py`
- Modify: `backend/schemas/meta_ads.py`, `backend/routers/meta_ads_router.py`, `backend/models/__init__.py`
- Test: `backend/tests/test_meta_ads_config_monitor.py`

**Interfaces:**
- Produces:
  - `MetaAdsMonitorConfig` (um por empresa, único `mmcEmpId`): `mmcEtkMqlId`, `mmcEtkOportunidadeId` (FK etapa, SET NULL), `mmcCplFator` Numeric(5,2)=1.5, `mmcGastoSemLead` Numeric(14,2)=150, `mmcFrequenciaMax` Numeric(5,2)=3, `mmcQuedaCtrPct` int=30, `mmcHorasSemContato` int=24, `mmcGastoMinRanking` Numeric(14,2)=50, `mmcHoraResumo` int=8, `mmcAlertaCpl`, `mmcAlertaGasto`, `mmcAlertaFrequencia`, `mmcAlertaCtr`, `mmcAlertaParado`, `mmcAlertaSemContato` (bool, True), `mmcSemContatoDesde` (DateTime tz — preenchido com agora quando `mmcAlertaSemContato` passa a True ou na criação), auditoria.
  - `config_monitor.obter_config(db, emp_id) -> MetaAdsMonitorConfig` — cria com padrões se não existir; estágio de MQL padrão = estágio da empresa cujo nome normalizado é `"reunião de levantamento"`, oportunidade = `"reunião de vendas"` (pipeline `default`); se não achar, `None`.
  - `config_monitor.atualizar_config(db, emp_id, data: MetaAdsMonitorConfigUpdate) -> MetaAdsMonitorConfigResponse` — valida que os estágios são da empresa (`BadRequestError("Estágio inválido para esta empresa")`), fatores > 0, hora 0–23.
  - Rotas: `GET /api/meta-ads/monitoramento/config` (usuário da empresa), `PUT /api/meta-ads/monitoramento/config` (admin). Schemas `MetaAdsMonitorConfigResponse` / `MetaAdsMonitorConfigUpdate` com nomes de campo iguais às colunas sem prefixo (`etapaMqlId`, `etapaOportunidadeId`, `cplFator`, `gastoSemLead`, `frequenciaMax`, `quedaCtrPct`, `horasSemContato`, `gastoMinRanking`, `horaResumo`, `alertas: dict[str, bool]` com chaves `cpl, gasto, frequencia, ctr, parado, semContato`).

- [ ] **Step 1: Testes que falham**
  - `test_cria_com_padroes_e_acha_estagios_por_nome` (estágios "Reunião de Levantamento" e "Reunião de Vendas" na empresa).
  - `test_estagios_inexistentes_ficam_nulos`.
  - `test_estagio_de_outra_empresa_recusado`.
  - `test_religar_sem_contato_atualiza_data_inicio`.
  - `test_put_exige_admin` (TestClient como em `test_meta_ads_router`).
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar.**
- [ ] **Step 5: Commit** — `Meta Ads: configuração do monitoramento por empresa`.

---

### Task 8: Funil — datas de MQL e oportunidade, interação humana

**Files:**
- Create: `backend/services/meta_ads/funil.py`
- Test: `backend/tests/test_meta_ads_funil.py`

**Interfaces:**
- Consumes: Task 4 (`OportunidadeEtapaHistorico`), Task 7 (`obter_config`).
- Produces:
  - `estagios_que_contam(db, etk_id: int) -> list[int]` — o próprio estágio + estágios ativos do mesmo pipeline e empresa com `etkOrdem` **maior**.
  - `primeiras_datas(db, emp_id: int, etk_id: int | None) -> dict[int, date]` — por oportunidade, a menor `oehData` (data local America/Sao_Paulo) em transição para um dos estágios de `estagios_que_contam`; oportunidades ganhas sem essa transição entram com `opoDataFechamento`. `etk_id None` → `{}`.
  - `primeira_interacao(db, emp_id: int) -> dict[int, datetime]` — por oportunidade, a menor entre: primeira transição com `oehEtkIdDe` não nulo; primeiro `OportunidadeHistorico` com `ophUsuId` não nulo e ativo; `opoDataFechamento` (00:00).
  - `@dataclass FunilLead(opo_id, mcg_id, man_id, recebido: date | None, mql: date | None, oportunidade: date | None, contrato: date | None, mrr: float, projeto: float, horas_primeiro_contato: float | None)`.
  - `carregar_funil(db, emp_id: int, condicao_meta) -> list[FunilLead]` — leads ativos da empresa que satisfazem `condicao_meta` (expressão SQLAlchemy); MRR/projeto pelas expressões da fase 1 (`_mrr_incremental_expr`, `_valor_projeto_expr`) aplicadas por oportunidade.
  - `contar(funil: list[FunilLead], inicio: date | None, fim: date | None, chave) -> dict` — agrupa por `chave(lead)` e devolve `{chave: {"leadsCrm", "mqls", "oportunidades", "contratos", "mrr", "projeto", "horasPrimeiroContatoMedia"}}` contando cada etapa pela própria data no período; MRR/projeto somados para contratos no período.

- [ ] **Step 1: Testes que falham** (SQLite, estágios: Contatos 1, Qualificado 2, Pré Reunião 3, Reunião de Levantamento 3, Reunião de Vendas 4, Negociação 9):
  - `test_mql_pela_primeira_chegada`: Contatos→Levantamento (05/10)→Contatos (06/10)→Levantamento (08/10) → MQL 05/10.
  - `test_pular_para_estagio_posterior_conta`: Contatos→Negociação (07/10) → MQL e oportunidade 07/10.
  - `test_estagio_de_mesma_ordem_nao_conta`: Contatos→Pré Reunião → sem MQL.
  - `test_ganho_sem_passagem_usa_fechamento`.
  - `test_interacao_humana`: só registros automáticos → `None`; transição saindo de Contatos às 10:00 → 10:00; histórico com `ophUsuId` às 09:00 → 09:00.
  - `test_contar_por_evento_no_periodo`: lead recebido 28/09, MQL 02/10, ganho 20/10; período outubro → `leadsCrm 0, mqls 1, contratos 1`.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar** com consultas agregadas (sem N+1).
- [ ] **Step 4: Rodar e ver passar.**
- [ ] **Step 5: Commit** — `Meta Ads: funil por estágio (MQL, oportunidade, contrato)`.

---

### Task 9: Painel por criativo, CPL Meta e regra "lead da Meta" por conta

**Files:**
- Modify: `backend/services/meta_ads/indicadores.py`, `backend/schemas/meta_ads.py`, `backend/routers/meta_ads_router.py`, `backend/services/meta_ads/contas.py` + schemas de conta (`macExigirRastreio` no create/update/response)
- Test: `backend/tests/test_meta_ads_indicadores.py`, `backend/tests/test_meta_ads_contas.py`

**Interfaces:**
- Consumes: Task 3 (insights por anúncio), Task 5 (`tem_sinal_meta`, `macExigirRastreio`), Task 8 (`carregar_funil`, `contar`).
- Produces:
  - `MetaAdsLinha` ganha: `nivel: Literal["campanha","conjunto","anuncio","nao_identificada","total"]`, `id: int | None` (mcg/mcj/man), `custoLeadCrm`, `mqls`, `custoMql`, `oportunidades`, `custoOportunidade`, `horasPrimeiroContato`, `filhos: list["MetaAdsLinha"] = []`. `cpl` passa a ser **investimento ÷ leadsMeta**; `vendas` = contratos; `cac` = investimento ÷ contratos. `mcgId` permanece (compatibilidade da faixa do Dashboard e do detalhe).
  - `MetaAdsPainelResponse` ganha `cobertura: float | None` (% de leads Meta do período com `opoMetaAnuncioId`) e `revisaoOrigem: list[MetaAdsRevisaoItem]` (`opoId, opoTitulo, opoNomeContato, opoDataRecebimento`).
  - Regra "lead da Meta" por conta: para contas com `macExigirRastreio = True`, só leads com `tem_sinal_meta`; os de origem mapeada sem sinal vão para `revisaoOrigem` e não entram em nenhum número. Contas com `False` mantêm a regra da fase 1. Com filtro de conta, vale a flag daquela conta; sem filtro, vale por empresa = `True` se qualquer conta ativa da empresa tiver a flag.
  - Árvore: linhas de campanha com `filhos` = conjuntos com `filhos` = anúncios; gasto do anúncio de `meta_ads_insight_anuncio_diario`; leads/MQL/… do anúncio por `opoManId`; da campanha por `opoMcgId` (leads sem anúncio resolvido somam só na campanha).

- [ ] **Step 1: Testes que falham** (estende o setUp existente com conjunto/anúncios e insights por anúncio):
  - `test_cpl_principal_usa_leads_meta`: c1 investimento 300, leadsMeta 4 → `cpl == 75.0`; `custoLeadCrm == 150.0`.
  - `test_arvore_campanha_conjunto_anuncio` (soma dos filhos = pai em investimento).
  - `test_funil_por_anuncio`: lead com `opoManId` do anúncio A que virou MQL e oportunidade no período → A `mqls 1`, `oportunidades 1`, `custoMql == investimento_A`.
  - `test_exigir_rastreio_tira_origem_sem_sinal`: com a flag, lead C (origem Anúncios sem sinal) sai de `naoIdentificada` e aparece em `revisaoOrigem`; totais sem ele.
  - `test_sem_flag_mantem_regra_da_fase_1` (os testes antigos continuam passando sem alteração de valores, exceto `cpl`, que agora usa leads Meta — atualizar as asserções antigas de `cpl` para a nova fórmula).
  - `test_cobertura`: 3 leads Meta, 2 com `opoMetaAnuncioId` → `cobertura == 66.67`.
  - `test_bate_com_a_aba_fontes` continua verde.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar** + suíte completa (`test_mcp_*`, `test_meta_ads_router`).
- [ ] **Step 5: Commit** — `Meta Ads: painel por criativo com funil, CPL Meta e revisão de origem`.

---

### Task 10: Página Campanhas por criativo

**Files:**
- Modify: `frontend/src/pages/Campanhas/metaAdsTipos.ts`, `CampanhasPage.tsx`, `CampanhaDetalheModal.tsx` (só tipos), `frontend/src/pages/Integracoes/MetaAdsContasPage.tsx` (caixa "Contar só leads com rastreio da Meta" no formulário da conta), `frontend/src/styles.css`

**Interfaces:**
- Consumes: Task 9 (`MetaAdsLinha` com `nivel`, `filhos`, `cpl` Meta, `custoLeadCrm`, `mqls`, `custoMql`, `oportunidades`, `custoOportunidade`, `horasPrimeiroContato`; `cobertura`; `revisaoOrigem`).

- [ ] **Step 1:** Tipos em `metaAdsTipos.ts` iguais ao schema da Task 9.
- [ ] **Step 2:** Tabela em árvore: linha de campanha com botão ▸/▾ que mostra conjuntos, e conjunto que mostra anúncios (recuo por nível); estado de expansão por id em `useState<Set<string>>`. Colunas: Campanha/Anúncio, Status, Investimento, Impressões, Cliques, CTR, CPC, Leads Meta, CPL, Leads CRM, Custo/lead CRM, MQLs, Custo/MQL, Oportunidades, Custo/oportunidade, Contratos, CAC, MRR, Projeto, Retorno, Tempo até 1º contato (h). Clique no nome da campanha continua abrindo o detalhe.
- [ ] **Step 3:** Cartões de topo: Investimento, Leads Meta, CPL, MQLs, Custo/MQL, Oportunidades, Contratos, CAC, Retorno, **Cobertura de rastreio** (com dica "% dos leads da Meta com ID do anúncio; meta ≥ 90%").
- [ ] **Step 4:** Seção "Origem Anúncios sem registro na Meta" abaixo da tabela, só quando `revisaoOrigem.length > 0`: título, explicação curta, tabela (lead com link para `/oportunidades/:id`, contato, recebido).
- [ ] **Step 5:** Remover o cartão de título duplicado (o cabeçalho vem do `Layout`).
- [ ] **Step 6:** Verificar: `npx tsc --noEmit -p . 2>&1 | grep -c "error TS"` → 6; `npm run build` OK.
- [ ] **Step 7: Commit** — `Campanhas: visão por conjunto e anúncio com funil e cobertura`.

---

### Task 11: Avaliação dos alertas — regras puras

**Files:**
- Create: `backend/services/meta_ads/alertas.py` (só a parte pura nesta task)
- Test: `backend/tests/test_meta_ads_alertas_regras.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Disparo(tipo: str, chave: str, mensagem: str, dados: dict)`; tipos: `"cpl"`, `"gasto"`, `"frequencia"`, `"ctr"`, `"parado"`, `"sem_contato"`; chave `"anuncio:<manId>"`, `"conta:<macId>"`, `"campanha:<mcgId>"`, `"lead:<opoId>"`.
  - `regra_cpl(man_id, nome, gasto_ontem, leads_ontem, gasto_base, leads_base, fator) -> Disparo | None` — dispara se `leads_ontem ≥ 1`, `leads_base ≥ 1` e `gasto_ontem/leads_ontem > fator × gasto_base/leads_base`.
  - `regra_gasto(man_id, nome, gasto_7d, leads_7d, limite) -> Disparo | None` — `leads_7d == 0 and gasto_7d >= limite`.
  - `regra_frequencia(man_id, nome, frequencia_7d, maximo) -> Disparo | None` — `> maximo`.
  - `regra_ctr(man_id, nome, ctr_inicial, imp_inicial, ctr_atual, imp_atual, dias_veiculacao, queda_pct) -> Disparo | None` — exige `dias_veiculacao >= 14`, `imp_inicial >= 1000`, `imp_atual >= 1000`, `ctr_atual <= ctr_inicial × (1 − queda_pct/100)`.
  - `regra_anuncio_reprovado(man_id, nome, status, motivo)` — `status in {"DISAPPROVED", "WITH_ISSUES"}`.
  - `regra_conta(mac_id, nome, account_status, disable_reason)` — `account_status not in (None, 1)`; mensagem com o significado (`2` desativada, `3` pagamento pendente, `7` em análise de risco, `8` pagamento pendente, `9` período de carência, `100`/`101` encerrada).
  - `regra_campanha_sem_veicular(mcg_id, nome, status, impressoes_ontem)` — `status == "ACTIVE" and impressoes_ontem == 0`.
  - `regra_sem_contato(opo_id, titulo, contato, telefone, recebido_em, agora, horas, desde) -> Disparo | None` — `recebido_em >= desde` e `agora − recebido_em > horas`; **único** que põe nome e telefone em `dados`/`mensagem`.
  - Mensagens curtas em português com o número que disparou (ex.: `CPL de ontem R$ 92,00 (2,3× a média de R$ 40,00 dos 7 dias anteriores).`).

- [ ] **Step 1: Testes que falham** — para cada regra: um caso que dispara com os limites padrão (1,5; 150; 3; 30%; 24 h) e um no limite exato que **não** dispara (ex.: CPL exatamente 1,5× não dispara; gasto R$ 149,99 não dispara; frequência 3,0 não dispara; lead recebido antes de `desde` não dispara); `test_sem_contato_e_o_unico_com_dados_pessoais` (nenhuma outra regra tem chaves `contato`/`telefone` em `dados`).
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar.**
- [ ] **Step 5: Commit** — `Meta Ads: regras de alerta`.

---

### Task 12: Alertas — coleta, persistência e agendamento

**Files:**
- Create: `backend/models/meta_ads_alerta.py` (alias `mal`), `backend/alembic/versions/0035_meta_ads_alerta.py` (down `0034_monitor_config`)
- Modify: `backend/services/meta_ads/alertas.py`, `backend/workers/meta_ads_worker.py`, `backend/services/meta_ads/sincronizacao.py` (expor `cliente_da_conta(db, mac_id)` reutilizável para chamadas leves), `backend/schemas/meta_ads.py`, `backend/routers/meta_ads_router.py`, `backend/models/__init__.py`
- Test: `backend/tests/test_meta_ads_alertas.py`, `backend/tests/test_meta_ads_worker.py`

**Interfaces:**
- Consumes: Task 11 (regras), Task 2 (`frequencia_7_dias`, `listar_anuncios`, `obter_status_conta`), Task 3 (tabelas), Task 7 (config), Task 8 (`primeira_interacao`), Task 5 (`tem_sinal_meta`).
- Produces:
  - `MetaAdsAlerta`: `malId, malEmpId, malTipo (20), malChave (60), malStatus (aberto|ciente|resolvido), malMensagem (500), malDados JSON, malPrimeiroEm, malUltimoEm, malResolvidoEm`; índice `(malEmpId, malStatus)`; único parcial não suportado → regra no código: no máximo um não-resolvido por `(malEmpId, malTipo, malChave)`.
  - `alertas.sincronizar_disparos(db, emp_id, tipos: set[str], disparos: list[Disparo], agora) -> dict` — para os `tipos` avaliados: disparo novo → cria `aberto`; disparo de alerta existente não resolvido → atualiza mensagem/dados/`malUltimoEm` (mantém `ciente` se estava ciente); alerta não resolvido daqueles tipos sem disparo → `resolvido`. Devolve contagens. Commit.
  - `alertas.avaliar_diarios(db, emp_id, hoje: date, fabrica_cliente=ClienteGraph) -> dict` — tipos `cpl, gasto, frequencia, ctr` (+ `parado` com os dados do banco), lendo `meta_ads_insight_anuncio_diario`; frequência via `frequencia_7_dias` de cada conta ativa (erro da Meta → pula `frequencia` sem resolver os abertos desse tipo). Respeita os liga/desliga da config.
  - `alertas.avaliar_horarios(db, emp_id, agora: datetime, fabrica_cliente=ClienteGraph) -> dict` — `parado` (status de anúncios e conta frescos da Meta, sem gravar insights) e `sem_contato` (leads com sinal de Meta, abertos, `opoDataCriacao >= mmcSemContatoDesde`, sem `primeira_interacao`).
  - `alertas.listar(db, emp_id, status: str | None) -> list[MetaAdsAlertaResponse]` e `alertas.marcar_ciente(db, emp_id, mal_id) -> MetaAdsAlertaResponse` (404 para outra empresa).
  - Rotas: `GET /api/meta-ads/alertas?status=aberto` (usuário), `POST /api/meta-ads/alertas/{mal_id}/ciente` (usuário).
  - Worker: `_ciclo` diário chama, após a sync, `avaliar_diarios` para cada empresa com conta ativa; novo laço de hora em hora (`segundos_ate_proxima_hora(agora) -> float`, na hora cheia seguinte) chama `avaliar_horarios` e o gatilho do resumo (Task 13: `resumo.gerar_se_devido`). Falha numa empresa não impede as outras.

- [ ] **Step 1: Testes que falham**
  - `test_alerta_nao_duplica_e_resolve`: disparo X no dia 1 → 1 aberto; mesmo disparo no dia 2 → continua 1 (mensagem atualizada); dia 3 sem disparo → `resolvido`; dia 4 com disparo → novo `aberto` (2 linhas no total).
  - `test_ciente_continua_ciente_enquanto_dispara`.
  - `test_avaliar_diarios_gasto_sem_lead` (insights por anúncio: R$ 160 em 7 dias, 0 leads → 1 alerta `gasto`).
  - `test_avaliar_diarios_respeita_desligado`.
  - `test_erro_na_frequencia_nao_resolve_abertos`.
  - `test_lead_sem_contato_ignora_backlog`: lead de antes de `mmcSemContatoDesde` → nada; lead depois, 25 h sem interação → 1 alerta com nome e telefone; após mover de Contatos → `resolvido` na avaliação seguinte.
  - `test_marcar_ciente_de_outra_empresa_404`.
  - `test_meta_ads_worker`: `test_segundos_ate_proxima_hora` (10:15:30 → 2670 s; 10:00:00 → 3600 s).
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar** + suíte completa.
- [ ] **Step 5: Commit** — `Meta Ads: alertas com deduplicação, avaliação diária e de hora em hora`.

---

### Task 13: Resumo diário

**Files:**
- Create: `backend/models/meta_ads_resumo.py` (alias `mrs`), `backend/alembic/versions/0036_meta_ads_resumo.py` (down `0035_meta_ads_alerta`), `backend/services/meta_ads/resumo.py`
- Modify: `backend/schemas/meta_ads.py`, `backend/routers/meta_ads_router.py`, `backend/models/__init__.py`
- Test: `backend/tests/test_meta_ads_resumo.py`

**Interfaces:**
- Consumes: Task 9 (`painel` com árvore), Task 7 (config), Task 12 (`alertas.listar`).
- Produces:
  - `MetaAdsResumo`: `mrsId, mrsEmpId, mrsData (Date — dia em que foi gerado), mrsInicio, mrsFim (período "anterior"), mrsDados JSON, mrsLeitura Text nullable, mrsAviso (300) nullable, mrsGeradoEm`; único `(mrsEmpId, mrsData)`.
  - `periodo_anterior(hoje: date) -> tuple[date, date]` — segunda-feira → (sexta, domingo); outros dias → (ontem, ontem).
  - `ranking(anuncios: list[MetaAdsLinha], gasto_min: float) -> tuple[list, list]` — elegíveis = investimento ≥ `gasto_min`; **melhores**: com `mqls > 0` por `custoMql` crescente, depois com leads por `cpl` crescente; **piores**: sem lead por investimento decrescente, depois os demais por `cpl` decrescente; no máximo 3 cada; um anúncio não aparece nas duas listas.
  - `montar_dados(db, emp_id, hoje) -> dict` — `{"periodo": {...}, "ultimos7": {...}, "comparacao": {...}, "campanhas": [...], "anuncios": [...], "melhores": [...], "piores": [...], "cobertura": x, "horasPrimeiroContato": h, "alertasAbertos": n}`; comparação usa **média diária** do período anterior × média diária dos 7 dias; **sem dados pessoais** (só ids, nomes de campanha/anúncio e números).
  - `gerar_leitura(dados: dict, provedor=None) -> tuple[str | None, str | None]` — usa `get_scope_provider().chat_completion([...], temperature=0.3)`; prompt de sistema em português: "Você é um analista de mídia paga. Em até dois parágrafos, diga o que mudou e o que vale olhar. Use só os números fornecidos. Não sugira ações na conta; recomende o que verificar." Erro ou sem chave → `(None, "Leitura por IA indisponível: <motivo curto>")`.
  - `gerar(db, emp_id, hoje: date, *, provedor=None) -> MetaAdsResumoResponse` — upsert por `(emp_id, hoje)`.
  - `gerar_se_devido(db, emp_id, agora: datetime) -> bool` — gera se dia útil (seg–sex), hora local ≥ `mmcHoraResumo`, empresa com conta ativa e ainda não há resumo de hoje.
  - Rotas: `GET /api/meta-ads/resumos?limite=30` (datas disponíveis), `GET /api/meta-ads/resumos/{data}` (`data` = `YYYY-MM-DD` ou `ultimo`; 404 se não houver), `POST /api/meta-ads/resumos/{data}/gerar` (usuário da empresa).

- [ ] **Step 1: Testes que falham**
  - `test_periodo_anterior`: segunda 26/10/2026 → (23/10, 25/10); terça 27/10 → (26/10, 26/10).
  - `test_ranking_regras`: casos com MQL, só leads, sem leads e abaixo do gasto mínimo → listas esperadas; nenhum repetido.
  - `test_dados_sem_dados_pessoais`: `json.dumps(dados)` não contém nome, telefone nem e-mail dos leads do setUp.
  - `test_leitura_falha_vira_aviso` (provedor falso que levanta) → `mrsLeitura is None`, `mrsAviso` começa com "Leitura por IA indisponível".
  - `test_gerar_se_devido`: sábado → False; segunda 07:59 → False; segunda 08:00 → True; segunda 09:00 com resumo já gerado → False.
  - `test_regerar_substitui`.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar** + suíte completa.
- [ ] **Step 5: Commit** — `Meta Ads: resumo diário com ranking e leitura por IA`.

---

### Task 14: Tela Monitoramento e configuração

**Files:**
- Create: `frontend/src/pages/Monitoramento/MonitoramentoPage.tsx`, `frontend/src/pages/Monitoramento/ConfigMonitoramentoModal.tsx`
- Modify: `frontend/src/pages/Campanhas/metaAdsTipos.ts` (tipos de resumo, alerta e config), `frontend/src/App.tsx` (rota `/monitoramento`), `frontend/src/components/Layout.tsx` (item "Monitoramento" no grupo CRM antes de "Campanhas"; `getHeaderData` e auto-expansão do CRM para `/monitoramento`), `frontend/src/styles.css`

**Interfaces:**
- Consumes: rotas das Tasks 7, 12 e 13.

- [ ] **Step 1:** Página com três blocos:
  - **Resumo**: seletor de data (lista de `GET /resumos`), botão "Gerar de novo"; cartões do período anterior e dos 7 dias (gasto, leads Meta, CPL, MQLs, custo/MQL, cobertura) com a variação; parágrafo da leitura (ou o aviso); tabelas "3 melhores" e "3 piores"; tabela por campanha. Sem resumo → "Nenhum resumo gerado ainda" + "Gerar agora".
  - **Alertas abertos**: lista com tipo (rótulo em português), mensagem, desde quando, link para o lead quando `tipo = sem_contato`, botão "Ciente". Filtro "mostrar cientes".
  - **Configurar** (só admin): abre `ConfigMonitoramentoModal` com selects de estágio (de `GET /etapas-kanban?pipeline=default`), os limites e os liga/desliga.
- [ ] **Step 2:** Tratamento de erro em cada chamada (mensagem `integracao-erro`), guarda contra resposta fora de ordem (`ativo` no efeito), como nas telas da fase 1.
- [ ] **Step 3:** Verificar: tsc = 6; build OK.
- [ ] **Step 4: Commit** — `Monitoramento: tela de resumo diário, alertas e configuração`.

---

### Task 15: Ferramentas MCP de campanhas

**Files:**
- Create: `backend/mcp_crm/ferramentas/campanhas.py`
- Modify: `backend/mcp_crm/ferramentas/__init__.py`
- Test: `backend/tests/test_mcp_ferramentas_campanhas.py`

**Interfaces:**
- Consumes: `indicadores.painel` (Task 9), `alertas.listar` (Task 12), `resumo` (Task 13); padrão de `mcp_crm/ferramentas/indicadores.py` (`@mcp.tool()`, `executar_ferramenta(ctx, nome, escrita=False, argumentos=...)`).
- Produces (todas `escrita=False`, sem dados pessoais):
  - `resumo_campanhas(ctx, data_inicial: date | None = None, data_final: date | None = None) -> dict` — total + campanhas (sem `filhos`).
  - `funil_por_criativo(ctx, data_inicial: date | None = None, data_final: date | None = None, campanha_id: int | None = None) -> dict` — anúncios com leads, MQLs, oportunidades, contratos e custos; ordenado por oportunidades decrescente.
  - `alertas_campanhas(ctx, status: Literal["aberto","ciente","resolvido"] = "aberto") -> dict` — para `sem_contato`, devolve só o id da oportunidade e as horas, **sem** nome/telefone.
  - `resumo_diario(ctx, data: date | None = None) -> dict` — o último se `data` for nulo.

- [ ] **Step 1: Testes que falham** (padrão de `test_mcp_ferramentas_leitura`, com `contexto_falso` e `usar_sessao`): uma chamada por ferramenta verificando as chaves da resposta; `test_alertas_sem_dados_pessoais` (alerta `sem_contato` com nome/telefone nos `dados` → resposta não contém nenhum dos dois).
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar** + `backend.tests.test_mcp_protocolo`.
- [ ] **Step 5: Commit** — `MCP: ferramentas de campanhas, funil por criativo, alertas e resumo`.

---

### Task 16: Implantação (controlador, com ok do Carlos em cada passo)

Executada pelo controlador da sessão, não por subagente. Cada item pede ok explícito do Carlos antes.

- [ ] **Step 1: Suíte e build** no branch: backend completo OK; tsc = 6; build OK.
- [ ] **Step 2: Migrations** `0031`–`0036` no banco do `.env` (`.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head`) e conferência das tabelas/colunas.
- [ ] **Step 3: Carga de estágios**: `.venv/Scripts/python -m backend.scripts.carga_etapas --empresa 2` (simulação) → mostrar contagens → com ok, `--aplicar`.
- [ ] **Step 4: Chave de integração** nova da Smart Data (escopo `leads:write`) pela tela Integrações → Chaves de API (o Carlos cria e guarda o segredo; ou o controlador cria pela API com o ok dele).
- [ ] **Step 5: Fluxo n8n "lead Recebido -> CRM -> Whats Pedro"** (`KbNb0JM8wdQo4jLb`): trocar "Insert rows in a table" por um HTTP Request `POST {CRM}/api/v1/leads` com cabeçalho `X-API-Key` (credencial n8n), corpo: `source: "Anúncios"`, `external_id` e `meta_lead_id` = `id` sem `l:`, `name: full_name`, `email`, `phone: phone_number` sem `p:`, `company: company_name`, `campaign_id`/`adset_id`/`ad_id` sem prefixo, `notes` = nome do formulário + perguntas e respostas (todas as colunas que não são campos padrão), `owner_email` do usuário 3; o nó "Avisar Pedro" continua, com o token do uazapi movido para uma credencial (Header Auth). Testar com uma linha de teste antes de publicar.
- [ ] **Step 6: Fluxo n8n de carga retroativa** (novo, manual): ler a planilha inteira, montar lotes de até 500 `RastreioMetaItem` e chamar `POST /api/v1/leads/rastreio-meta`; mostrar as contagens ao Carlos.
- [ ] **Step 7: Ligar a regra nova**: marcar "Contar só leads com rastreio da Meta" na conta da Smart Data; conferir a página Campanhas (cobertura, revisão de origem) e o resumo gerado manualmente.
- [ ] **Step 8: Documentação**: `docs/META_ADS.md` ganha seções "Monitoramento", "Fluxo n8n" e "Carga retroativa"; spec ganha seção "Ajustes na implementação"; commit.

---

## Ajustes em relação à especificação

1. A carga de estágios é um CLI com simulação, não um endpoint.
2. O ciclo de hora em hora roda no mesmo worker da fase 1.
3. As ferramentas MCP são quatro (resumo de campanhas, funil por criativo, alertas, resumo diário).
