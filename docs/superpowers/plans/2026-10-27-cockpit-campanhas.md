# Cockpit de Campanhas — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar a página Campanhas num cockpit de decisão: selos de saúde contra metas, funil do anúncio ao contrato com gargalo, tendência mensal/semanal, matriz de decisão dos criativos, saúde da operação, leitura do período por IA e "Pergunte ao analista". A tabela detalhada atual fica embaixo.

**Architecture:** As regras de decisão (selos, gargalo, quadrante, períodos) ficam num módulo puro `services/meta_ads/cockpit_regras.py`. O serviço `services/meta_ads/cockpit.py` monta a resposta a partir de `indicadores.painel`, que ganha uma variante que devolve também os leads e as campanhas incluídas para a série por intervalo, sem regra de contagem nova. A IA (leitura guardada por recorte e perguntas com limite diário) fica em `services/meta_ads/cockpit_ia.py` e recebe só o contexto agregado, que também é a resposta da ferramenta MCP nova. No frontend, componentes do cockpit numa pasta própria, gráficos em SVG feito à mão, sem dependência nova.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, `unittest` + SQLite em memória (`backend/tests/banco_sqlite.py`), IA via `services/llm/llm_factory.get_scope_provider().chat_completion(messages, temperature=...)`; React 18 + TS + Vite.

**Spec:** `docs/superpowers/specs/2026-10-27-cockpit-campanhas-design.md` (base: `docs/superpowers/specs/2026-10-26-monitoramento-campanhas-meta-design.md`). Protótipo aprovado: https://claude.ai/artifact/1UTtsohaiujPABL2t9cHCe (textos e ordem das seções).

## Global Constraints

- Nenhuma escrita na Meta.
- Toda consulta filtra pela empresa (`empresa_obrigatoria`). Configuração (metas) só admin (`_admin`); cockpit, leitura e perguntas para qualquer usuário da empresa.
- Nenhum nome, telefone ou e-mail de lead na resposta do cockpit, no contexto da IA, na leitura, nas respostas do chat ou no MCP. `revisaoOrigem` entra só como contagem.
- Os números do cockpit saem de `indicadores.painel` e de `funil.contar`. Nenhuma regra de contagem nova: a série por intervalo soma exatamente o total.
- Metas padrão: CPL **R$ 150,00**; taxa de MQL **10%**; meta implícita de custo por MQL = CPL ÷ (taxa ÷ 100) = **R$ 1.500**. "Atenção" do CPL e do custo por MQL até `mmcCplFator` (1,5×); "Atenção" da taxa a partir de **60%** da meta.
- Amostra pequena: menos de **5** leads no CRM no anúncio. Gargalo: só passagens com pelo menos **3** entradas na etapa de origem. Série mensal acima de **62** dias, senão semanal (segunda a domingo).
- IA: até **30** criativos de maior investimento no contexto; chat com até **6** trocas (12 mensagens) de histórico, papéis só `pergunta`/`resposta`, até **2.000** caracteres cada; pergunta até **500** caracteres; **30** perguntas por usuário por dia (America/Sao_Paulo).
- Selos: `bom`, `atencao`, `ruim`, `sem_dados`. Quadrantes: `escalar`, `otimizar_custo`, `rever_publico`, `pausar`, `aguardar_dados`.
- Mensagens e textos em português; nomes `<alias><Campo>` (`docs/DATABASE_GUIDELINES.md`).
- Testes: `.venv/Scripts/python -m unittest backend.tests.<modulo> -v` da raiz; suíte completa: `.venv/Scripts/python -m unittest $(ls backend/tests/test_*.py | sed 's#/#.#g; s#\.py$##' | tr '\n' ' ')`. Frontend: `npx tsc --noEmit -p .` em `frontend/` com exatamente **6** erros (pré-existentes) e `npm run build` OK.
- **Nunca** rodar `alembic upgrade` sem ok explícito do Carlos no momento (o banco do `.env` é o real). Isso fica na Task 10, executada pelo controlador.
- Nunca `git add -A`: o working tree tem alterações não relacionadas (`.venv/`, `__pycache__/`, `frontend/dist/`). Nunca commitar `frontend/dist`.
- Acessibilidade: contraste ≥ 4,5:1; selo e recomendação sempre com texto; gráficos com `role="img"` e `aria-label` com os valores; controles alcançáveis pelo teclado; sem emoji.

## Review Focus

1. **Criativo com 1 ou 2 leads**: recebe quadrante e a marca "amostra pequena", nunca uma recomendação sem aviso (Task 2: `test_amostra_pequena`).
2. **Filtro "Só campanhas ativas" e filtro de conta**: a série soma o total do cockpit com os filtros ligados (Task 3: `test_serie_soma_total_com_filtros`).
3. **Ano corrente sem dados no período anterior**: `anteriorTemDados` falso, para a tela não mostrar "↓ 100%" (Task 4: `test_anterior_sem_dados`).
4. **Histórico do chat adulterado** (papel `system`, texto enorme, mais de 12 mensagens): descartado, e as instruções vêm só do servidor (Task 6: `test_historico_filtrado`).
5. **Metas alteradas depois da leitura**: a leitura guardada passa a vir com `desatualizada = true` (Task 5: `test_mudar_meta_desatualiza`).

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `backend/models/meta_ads_monitor_config.py` | Modificar | Colunas de meta |
| `backend/alembic/versions/0037_metas_cockpit.py` | Criar | Colunas de meta |
| `backend/services/meta_ads/config_monitor.py`, `backend/schemas/meta_ads.py` | Modificar | Metas na config |
| `backend/services/meta_ads/cockpit_regras.py` | Criar | Regras puras: selos, gargalo, quadrante, períodos, intervalos |
| `backend/services/meta_ads/indicadores.py` | Modificar | `calcular_painel` e `serie_por_intervalo` |
| `backend/services/meta_ads/cockpit.py` | Criar | Monta a resposta do cockpit |
| `backend/models/meta_ads_cockpit_leitura.py`, `backend/alembic/versions/0038_cockpit_leitura.py` | Criar | Leitura guardada por recorte |
| `backend/models/meta_ads_pergunta_uso.py`, `backend/alembic/versions/0039_pergunta_uso.py` | Criar | Contagem diária de perguntas |
| `backend/services/meta_ads/cockpit_ia.py` | Criar | Contexto da IA, impressão digital, leitura, perguntas |
| `backend/exceptions.py` | Modificar | `TooManyRequestsError` (429) |
| `backend/routers/meta_ads_router.py` | Modificar | Rotas do cockpit, leitura e perguntas |
| `backend/models/__init__.py` | Modificar | Registrar modelos novos |
| `backend/mcp_crm/ferramentas/campanhas.py` | Modificar | Ferramenta `cockpit_campanhas` |
| `frontend/src/pages/Campanhas/metaAdsTipos.ts` | Modificar | Tipos, rótulos, `intervaloUltimosDias` |
| `frontend/src/pages/Campanhas/cockpit/*.tsx` | Criar | Componentes do cockpit |
| `frontend/src/pages/Campanhas/CampanhasPage.tsx` | Modificar | Filtros, composição, tabela detalhada embaixo |
| `frontend/src/pages/Monitoramento/ConfigMonitoramentoModal.tsx` | Modificar | Seção "Metas do cockpit" |
| `frontend/src/styles.css` | Modificar | Classes `.cockpit-*` |
| `docs/META_ADS.md` | Modificar | Seção "Cockpit" |

---

### Task 1: Metas na configuração do monitoramento

**Files:**
- Modify: `backend/models/meta_ads_monitor_config.py`, `backend/services/meta_ads/config_monitor.py`, `backend/schemas/meta_ads.py`, `frontend/src/pages/Campanhas/metaAdsTipos.ts` (`MonitorConfig`), `frontend/src/pages/Monitoramento/ConfigMonitoramentoModal.tsx`
- Create: `backend/alembic/versions/0037_metas_cockpit.py` (revision `0037_metas_cockpit`, down `0036_meta_ads_resumo`; adiciona as duas colunas só se não existirem, no padrão idempotente da 0036; downgrade remove)
- Test: `backend/tests/test_meta_ads_config_monitor.py`

**Interfaces:**
- Produces:
  - Colunas `mmcMetaCpl: Numeric(14,2)`, NOT NULL, padrão `150`; `mmcMetaTaxaMql: Numeric(5,2)`, NOT NULL, padrão `10` (com `server_default` na migration para linhas existentes).
  - `MetaAdsMonitorConfigResponse` ganha `metaCpl: float`, `metaTaxaMql: float`. `MetaAdsMonitorConfigUpdate` ganha `metaCpl: float | None = Field(None, gt=0, le=1_000_000)`, `metaTaxaMql: float | None = Field(None, ge=0.1, le=100)`. Entram em `_NUMERICOS` (`("mmcMetaCpl", True)`, `("mmcMetaTaxaMql", True)`).
  - `obter_config` cria com `mmcMetaCpl=Decimal("150")`, `mmcMetaTaxaMql=Decimal("10")`.

- [ ] **Step 1: Testes que falham**
  - `test_metas_padrao`: config nova → `metaCpl == 150.0`, `metaTaxaMql == 10.0`.
  - `test_atualiza_metas`: PUT com `metaCpl=180, metaTaxaMql=12.5` → resposta e banco com os valores.
  - `test_meta_taxa_fora_do_limite`: `MetaAdsMonitorConfigUpdate(metaTaxaMql=0)` e `(metaTaxaMql=101)` levantam `ValidationError`; `metaCpl=0` também.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar** o modelo, a migration, o schema e o serviço. No modal, uma seção "Metas do cockpit" com "Meta de CPL (R$)" (passo 0,01) e "Meta de taxa de MQL (%)" (passo 0,1), usando o `campoNumero` existente; `MonitorConfig` ganha os dois campos.
- [ ] **Step 4: Rodar e ver passar** + `backend.tests.test_meta_ads_router`; tsc = 6.
- [ ] **Step 5: Commit**: `Cockpit: metas de CPL e taxa de MQL na configuração do monitoramento`.

---

### Task 2: Regras puras do cockpit

**Files:**
- Create: `backend/services/meta_ads/cockpit_regras.py`
- Test: `backend/tests/test_meta_ads_cockpit_regras.py`

**Interfaces:**
- Produces (todas puras, sem banco):
  - `Selo = Literal["bom", "atencao", "ruim", "sem_dados"]`; `Quadrante = Literal["escalar", "otimizar_custo", "rever_publico", "pausar", "aguardar_dados"]`; `Passagem = Literal["mql", "oportunidade", "contrato"]` (nome do destino da passagem).
  - `@dataclass(frozen=True) class Metas: cpl: float; taxa_mql: float; fator: float; gasto_sem_lead: float`, com a propriedade `custo_mql_implicito -> float` (= `cpl / (taxa_mql / 100)`). `metas_da_config(cfg: MetaAdsMonitorConfig) -> Metas` usa `mmcMetaCpl`, `mmcMetaTaxaMql`, `mmcCplFator`, `mmcGastoSemLead`.
  - `taxa(parte: int, base: int) -> float | None`: percentual com 2 casas, `None` se a base for 0.
  - `selo_cpl(cpl: float | None, m: Metas) -> Selo`; `selo_taxa_mql(mqls: int, leads_crm: int, m: Metas) -> Selo`; `selo_custo_mql(custo_mql: float | None, m: Metas) -> Selo`.
  - `saude_periodo(cpl: Selo, taxa_mql: Selo) -> Selo`: `sem_dados` se o selo do CPL for `sem_dados`; senão o pior entre os dois, na ordem `ruim > atencao > bom` e ignorando `sem_dados`.
  - `gargalo(leads_crm: int, mqls: int, oportunidades: int, contratos: int) -> Passagem | None`: passagens elegíveis são as com base ≥ 3; vence a de menor taxa; no empate, a mais cedo no funil.
  - `frase_gargalo(passagem: Passagem, base: int, chegaram: int) -> str | None`.
  - `@dataclass(frozen=True) class Classificacao: quadrante: Quadrante; motivo: Literal["sem_lead", "sem_crm"] | None; amostra_pequena: bool; cpl: float | None; taxa_mql: float | None`.
  - `classificar_anuncio(investimento: float, leads_meta: int, leads_crm: int, mqls: int, m: Metas) -> Classificacao`. Regras da spec 5.7. CPL = investimento ÷ leads Meta; com 0 lead Meta e lead no CRM, CPL = investimento ÷ leads CRM (ver "Ajustes"). Sem lead Meta e sem lead CRM: `pausar` se investimento ≥ `gasto_sem_lead`, senão `aguardar_dados` com motivo `sem_lead`. Com lead Meta e 0 no CRM: `aguardar_dados` com motivo `sem_crm`. `amostra_pequena = leads_crm < 5` (falso em `aguardar_dados`).
  - `recomendacao(c: Classificacao, ativo: bool) -> tuple[str, str]`: `(rótulo, por quê)`. Textos de "por quê" são os do protótipo e da tabela 5.7 da spec. Os rótulos são "Escalar", "Otimizar custo", "Rever público", "Pausar" e "Aguardar dados". Com `ativo=False`, "Pausar" vira "Manter pausado" e o porquê ganha " (já pausado)". O porquê de `aguardar_dados` é "Gasto ainda baixo e nenhum lead: aguardar mais dados." (`sem_lead`) ou "Os leads ainda não chegaram ao CRM com este anúncio." (`sem_crm`). Com amostra pequena, o porquê termina com " Amostra pequena: menos de 5 leads."
  - `periodo_anterior(inicio: date, fim: date) -> tuple[date, date]`: mesmo número de dias, terminando na véspera de `inicio`.
  - `intervalos(inicio: date, fim: date) -> tuple[Literal["mes", "semana"], list[tuple[date, date, str]]]`: mensal se `(fim - inicio).days + 1 > 62`, senão semanal; cortados nas pontas. Rótulo mensal `"ago/2026"`; rótulo semanal `"05/10–11/10"`.

- [ ] **Step 1: Testes que falham** (`m = Metas(150, 10, 1.5, 150)`)
  - `test_metas`: `m.custo_mql_implicito == 1500`.
  - `test_selo_cpl`: 150 → bom; 225 → atencao; 225.01 → ruim; None → sem_dados.
  - `test_selo_taxa_mql`: (1, 10) → bom; (6, 100) → atencao; (5, 100) → ruim; (0, 0) → sem_dados.
  - `test_selo_custo_mql`: 1500 → bom; 2250 → atencao; 2675.33 → ruim; None → sem_dados.
  - `test_saude_periodo`: (atencao, ruim) → ruim; (sem_dados, bom) → sem_dados; (bom, sem_dados) → bom; (bom, atencao) → atencao.
  - `test_gargalo`: (36, 3, 1, 0) → "mql"; (10, 5, 1, 0) → "oportunidade"; (2, 1, 1, 0) → None; (10, 5, 5, 0) → "contrato"; empate (10, 5, 4, 2) com taxas 50/80/50 → "mql".
  - `test_frase_gargalo`: ("mql", 36, 3) → "Para cada 12 leads no CRM, só 1 vira MQL."; ("mql", 36, 0) → "Nenhum dos 36 leads no CRM virou MQL."; ("oportunidade", 9, 3) → "Para cada 3 MQLs, só 1 vira oportunidade."; ("contrato", 4, 0) → "Nenhuma das 4 oportunidades virou contrato."; chegaram ≥ base → None.
  - `test_classificar_dados_reais`:
    - (2522.88, 8, 7, 2) → otimizar_custo, cpl 315.36, taxa 28.57, sem amostra pequena;
    - (1778.29, 15, 14, 1) → rever_publico, cpl 118.55;
    - (1162.89, 3, 3, 0) → pausar com amostra pequena;
    - (90, 1, 1, 1) → escalar com amostra pequena.
  - `test_classificar_sem_lead`: (100, 0, 0, 0) → aguardar_dados com motivo sem_lead; (150, 0, 0, 0) → pausar; (200, 2, 0, 0) → aguardar_dados com motivo sem_crm; (100, 0, 2, 1) → cpl 50 (base CRM), escalar.
  - `test_amostra_pequena`: (90, 4, 4, 1) → amostra_pequena True; (90, 5, 5, 1) → False; e `recomendacao(...)[1]` termina com "Amostra pequena: menos de 5 leads.".
  - `test_recomendacao_pausado`: pausar com `ativo=False` → rótulo "Manter pausado" e o porquê contém "(já pausado)"; escalar com `ativo=True` → "Escalar".
  - `test_periodo_anterior`: (01/10/2026, 31/10/2026) → (31/08/2026, 30/09/2026); (01/01/2026, 27/10/2026) → (07/03/2025, 31/12/2025).
  - `test_intervalos`:
    - (01/01/2026, 27/10/2026) → "mes", 10 itens, o último (01/10, 27/10, "out/2026");
    - (01/10/2026, 31/10/2026) → "semana" com 5 itens: (01/10, 04/10), (05/10, 11/10), (12/10, 18/10), (19/10, 25/10), (26/10, 31/10);
    - 62 dias → semana; 63 dias → mes.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar.**
- [ ] **Step 5: Commit**: `Cockpit: regras de selo, gargalo, quadrante e períodos`.

---

### Task 3: Painel com série por intervalo

**Files:**
- Modify: `backend/services/meta_ads/indicadores.py`
- Test: `backend/tests/test_meta_ads_indicadores.py`

**Interfaces:**
- Produces:
  - `@dataclass class CalculoPainel: resposta: MetaAdsPainelResponse; leads_total: list[FunilLead]; campanhas_incluidas: set[int]`. `leads_total` é o `no_total` de hoje; `campanhas_incluidas` é o `incluidas` de hoje.
  - `calcular_painel(db, emp_id, filtro: FiltroPainel) -> CalculoPainel`: o corpo atual de `painel`. `painel(db, emp_id, filtro)` passa a ser `calcular_painel(...).resposta`, com comportamento idêntico.
  - `serie_por_intervalo(db, emp_id, filtro: FiltroPainel, calculo: CalculoPainel, faixas: list[tuple[date, date]]) -> list[dict]`: um dict por faixa, com as chaves `investimento, impressoes, cliques, leadsMeta, leadsCrm, mqls, oportunidades, vendas`.
    - Gasto: uma consulta em `MetaAdsInsightDiario` agrupada por `midData`, restrita a `midMcgId in campanhas_incluidas`, à empresa e à conta do filtro. Cada dia é somado na faixa a que pertence.
    - Funil: `contar(calculo.leads_total, ini, fim, lambda _l: 0)` por faixa.

- [ ] **Step 1: Testes que falham** (dados com `banco_sqlite`: 2 campanhas, uma ACTIVE e uma PAUSED, insights e leads em setembro e outubro, um lead sem campanha e um MQL)
  - `test_painel_inalterado`: os testes atuais de `test_meta_ads_indicadores` continuam passando (rodar o módulo inteiro).
  - `test_serie_soma_total`: faixas set/out → a soma de cada chave é igual ao campo correspondente de `resposta.total` (`vendas` ↔ `total.vendas`).
  - `test_serie_soma_total_com_filtros`: a mesma checagem com `somente_ativas=True` e com `mac_id` da conta.
  - `test_serie_por_faixa`: os valores de outubro são iguais aos de um `painel` com o filtro só de outubro.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar** + `test_meta_ads_resumo`, `test_mcp_ferramentas_campanhas`.
- [ ] **Step 5: Commit**: `Indicadores Meta: cálculo do painel reaproveitável e série por intervalo`.

---

### Task 4: Serviço e rota do cockpit

**Files:**
- Create: `backend/services/meta_ads/cockpit.py`
- Modify: `backend/schemas/meta_ads.py`, `backend/routers/meta_ads_router.py`
- Test: `backend/tests/test_meta_ads_cockpit.py`

**Interfaces:**
- Consumes: Task 1 (metas), Task 2 (regras), Task 3 (`calcular_painel`, `serie_por_intervalo`); `resumo._contar_alertas_abertos(db, emp_id)`. Pode ser renomeado para público `contar_alertas_abertos`, mantendo o uso em `resumo`.
- Produces:
  - Schemas (em `schemas/meta_ads.py`):
    - `MetaAdsCockpitMetas{cpl, taxaMql, custoMqlImplicito, cplFator}`.
    - `MetaAdsCockpitSelos{cpl, taxaMql, custoMql, saude}` (strings `Selo`).
    - `MetaAdsCockpitEtapa{chave: Literal["impressoes","cliques","leads","crm","mql","oportunidade","contrato"], quantidade: int, taxa: float | None, custo: float | None, gargalo: bool}`. A taxa é contra a etapa anterior (`None` na primeira). O custo é, na ordem: CPM (investimento ÷ impressões × 1000), CPC, CPL, `custoLeadCrm`, `custoMql`, `custoOportunidade`, `cac`.
    - `MetaAdsCockpitPonto{inicio, fim, rotulo, investimento, impressoes, cliques, leadsMeta, leadsCrm, mqls, cpl}`.
    - `MetaAdsCockpitCriativo{id, mcgId, nome, campanha, status, ativo, investimento, leadsMeta, leadsCrm, mqls, cpl, taxaMql, quadrante, motivo, amostraPequena, recomendacao, porque}`.
    - `MetaAdsCockpitOperacao{cobertura, horasPrimeiroContato, alertasAbertos, origemRevisar}`.
    - `MetaAdsCockpitResponse{temConta, inicio, fim, metas, total: MetaAdsLinha (sem filhos), taxaMql, anterior: MetaAdsLinha (sem filhos), anteriorInicio, anteriorFim, anteriorTemDados, selos, funil: list[MetaAdsCockpitEtapa], gargalo: str | None, fraseGargalo: str | None, intervalo: Literal["mes","semana"], serie: list[MetaAdsCockpitPonto], criativos: list[MetaAdsCockpitCriativo], operacao}`.
  - `cockpit.montar(db, emp_id, filtro: FiltroPainel) -> MetaAdsCockpitResponse`:
    - `filtro` com as duas datas; sem elas, `BadRequestError("Informe data inicial e final")`.
    - O período anterior usa o mesmo filtro com as datas de `periodo_anterior`. `anteriorTemDados = anterior.investimento > 0 or anterior.leadsMeta > 0 or anterior.leadsCrm > 0`.
    - Série: as faixas de `intervalos`, sem as faixas das pontas que não têm investimento, nem lead Meta, nem lead CRM (no meio, ficam zeradas).
    - Criativos: todos os anúncios da árvore com `investimento > 0`, mais os anúncios com lead e sem gasto, ordenados por investimento decrescente. `campanha` = nome da campanha-mãe e `ativo = status == "ACTIVE"`.
    - `operacao.origemRevisar = len(resposta.revisaoOrigem)`; os itens da lista **não** entram.
  - Rota `GET /api/meta-ads/cockpit` com `data_inicial`, `data_final` (obrigatórios), `macId`, `somente_ativas`, no mesmo padrão de `/painel`.

- [ ] **Step 1: Testes que falham** (banco SQLite como na Task 3, mais um anúncio PAUSED com gasto e um lead com nome, telefone e e-mail conhecidos)
  - `test_total_bate_com_painel`: `montar(...).total` tem os mesmos números de `painel(...).total`.
  - `test_anterior_e_variacao`: período de outubro → `anteriorInicio == 31/08`, `anteriorFim == 30/09`, números do anterior = painel de set.
  - `test_anterior_sem_dados`: período de 01/01 a 27/10 com dados só a partir de junho → `anteriorTemDados is False`.
  - `test_serie_aparada`: ano corrente com dados de agosto a outubro → `intervalo == "mes"` e a série começa em agosto.
  - `test_criativos_e_pausado`: o anúncio PAUSED aparece com `ativo False` e, se `pausar`, `recomendacao == "Manter pausado"`.
  - `test_funil_e_gargalo`: com 36 leads CRM e 3 MQLs (dados montados), `gargalo == "mql"` e a etapa `mql` tem `gargalo True`.
  - `test_sem_dados_pessoais`: `json.dumps(resposta.model_dump(mode="json"))` não contém o nome, o telefone nem o e-mail do lead; `operacao.origemRevisar` conta o lead em revisão.
  - `test_rota_exige_datas`: `GET /api/meta-ads/cockpit` sem datas → 400 (ou 422); com datas → 200 (TestClient como em `test_meta_ads_router`).
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar** + suíte completa.
- [ ] **Step 5: Commit**: `Cockpit: serviço e rota com selos, funil, série e criativos`.

---

### Task 5: Leitura do analista (IA) e ferramenta MCP

**Files:**
- Create: `backend/services/meta_ads/cockpit_ia.py`, `backend/models/meta_ads_cockpit_leitura.py` (alias `mcl`), `backend/alembic/versions/0038_cockpit_leitura.py` (down `0037_metas_cockpit`)
- Modify: `backend/models/__init__.py`, `backend/schemas/meta_ads.py`, `backend/routers/meta_ads_router.py`, `backend/mcp_crm/ferramentas/campanhas.py`
- Test: `backend/tests/test_meta_ads_cockpit_ia.py`, `backend/tests/test_mcp_ferramentas_campanhas.py`

**Interfaces:**
- Consumes: Task 4 (`cockpit.montar`), `resumo.PREFIXO_AVISO`, `resumo._motivo`.
- Produces:
  - `MetaAdsCockpitLeitura` (tabela `meta_ads_cockpit_leitura`):
    - Colunas: `mclId`, `mclEmpId` (FK empresa CASCADE), `mclInicio` Date, `mclFim` Date, `mclMacId` int NOT NULL (0 = todas as contas, sem FK), `mclSomenteAtivas` bool, `mclDigest` String(64), `mclLeitura` JSON, `mclGeradoEm` DateTime tz.
    - Único `(mclEmpId, mclInicio, mclFim, mclMacId, mclSomenteAtivas)`.
    - Migration idempotente no padrão da 0036.
  - `contexto_ia(c: MetaAdsCockpitResponse) -> dict` com as chaves `periodo, metas, total, anterior, anteriorTemDados, taxaMql, selos, funil, gargalo, fraseGargalo, intervalo, serie, criativos, operacao`.
    - `total`/`anterior` levam só os números de `MetaAdsLinha` (sem `filhos`, `id`, `nivel`).
    - `criativos` vai limitado aos 30 de maior investimento.
    - Nenhum campo de lead.
  - `impressao_digital(contexto: dict) -> str` = sha256 de `json.dumps(contexto, sort_keys=True, ensure_ascii=False, default=str)`.
  - `PROMPT_LEITURA` (sistema). Pede JSON `{"manchete", "funciona", "problema", "olharAgora"}` em português simples, para leigo, e segue as regras da spec 5.11: só os números recebidos; avisar amostra pequena; nada de referência externa; nunca dizer que vai agir na conta.
  - `interpretar_leitura(texto: str) -> dict | None`: aceita JSON puro ou entre crases (```json); exige as quatro chaves com texto não vazio.
  - Schema `MetaAdsCockpitLeituraResponse{leitura: MetaAdsCockpitLeituraTexto | None, texto: str | None, geradoEm: datetime | None, desatualizada: bool, aviso: str | None, iaDisponivel: bool}`, com `MetaAdsCockpitLeituraTexto{manchete, funciona, problema, olharAgora}`. `mclLeitura` guarda `{"leitura": {...} | None, "texto": str | None}`. Quando a IA não devolve JSON válido, `texto` fica com a resposta crua.
  - `obter_leitura(db, emp_id, filtro) -> MetaAdsCockpitLeituraResponse`: busca pelo recorte e compara `mclDigest` com a impressão digital do contexto atual. `iaDisponivel` = `get_scope_provider()` não levanta.
  - `gerar_leitura(db, emp_id, filtro, *, provedor=None) -> MetaAdsCockpitLeituraResponse`:
    - chama `provedor.chat_completion([system, user=json do contexto], temperature=0.3)` e faz upsert no recorte;
    - em erro, não grava nem apaga: devolve a guardada (se houver) com `aviso = f"{PREFIXO_AVISO}: {motivo}"`.
  - Rotas `GET /api/meta-ads/cockpit/leitura` e `POST /api/meta-ads/cockpit/leitura`, com os mesmos parâmetros de query de `/cockpit`.
  - MCP `cockpit_campanhas(ctx, data_inicial: date, data_final: date) -> dict` = `contexto_ia(cockpit.montar(...))`, com `escrita=False`.

- [ ] **Step 1: Testes que falham** (`ProvedorFalso` como em `test_meta_ads_resumo`)
  - `test_contexto_sem_dados_pessoais`: o `json.dumps(contexto_ia(...))` não contém nome, telefone nem e-mail do lead do setUp; tem no máximo 30 criativos (montar 31 anúncios com gasto).
  - `test_interpretar_leitura`: JSON puro, JSON entre crases e JSON sem `olharAgora` (→ None).
  - `test_gerar_e_obter`: gerar com provedor que devolve JSON válido → obter devolve a leitura, `desatualizada False`.
  - `test_resposta_sem_json_vira_texto`: provedor devolve texto livre → `leitura None`, `texto` com o texto.
  - `test_mudar_meta_desatualiza`: gerar, depois `atualizar_config(metaCpl=200)` → obter com `desatualizada True`.
  - `test_falha_mantem_guardada`: gerar ok, depois gerar com provedor que levanta → resposta com a leitura antiga e `aviso` começando por "Leitura por IA indisponível"; banco inalterado.
  - `test_recorte_por_conta`: leitura com `mac_id=None` e com `mac_id=X` ficam em linhas diferentes.
  - MCP `test_cockpit_campanhas_sem_dados_pessoais` (padrão do arquivo, com `indicadores`/`cockpit` simulados): a resposta tem as chaves de `contexto_ia` e nenhum campo de lead.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar** + `backend.tests.test_mcp_protocolo`.
- [ ] **Step 5: Commit**: `Cockpit: leitura do analista por IA guardada por recorte e ferramenta MCP`.

---

### Task 6: Pergunte ao analista

**Files:**
- Create: `backend/models/meta_ads_pergunta_uso.py` (alias `mpu`), `backend/alembic/versions/0039_pergunta_uso.py` (down `0038_cockpit_leitura`)
- Modify: `backend/services/meta_ads/cockpit_ia.py`, `backend/exceptions.py`, `backend/models/__init__.py`, `backend/schemas/meta_ads.py`, `backend/routers/meta_ads_router.py`
- Test: `backend/tests/test_meta_ads_cockpit_ia.py`

**Interfaces:**
- Consumes: Task 5 (`contexto_ia`), `resumo.hoje_local()`.
- Produces:
  - `TooManyRequestsError(HTTPException)` com status 429, no padrão de `exceptions.py`.
  - `MetaAdsPerguntaUso` (tabela `meta_ads_pergunta_uso`): `mpuId`, `mpuUsuId` (FK usuario CASCADE), `mpuData` Date, `mpuQuantidade` int; único `(mpuUsuId, mpuData)`.
  - Schemas: `MetaAdsPerguntaMensagem{papel: str = Field(max_length=20), texto: str = Field(max_length=20_000)}`; `MetaAdsPerguntaRequest{dataInicial: date, dataFinal: date, macId: int | None = None, somenteAtivas: bool = False, pergunta: str (strip; 1..500), historico: list[MetaAdsPerguntaMensagem] = Field(default_factory=list, max_length=50)}`; `MetaAdsPerguntaResponse{resposta: str, restantesHoje: int}`.
  - `LIMITE_PERGUNTAS_DIA = 30`; `PROMPT_PERGUNTA` (regras da 5.11, mais: "se a pergunta não puder ser respondida com estes números, diga isso e sugira o que olhar"; resposta curta).
  - `filtrar_historico(historico: list[MetaAdsPerguntaMensagem]) -> list[dict]`: mantém só papel `pergunta`/`resposta` com texto não vazio de até 2.000 caracteres; fica com as 12 últimas; mapeia para `{"role": "user" | "assistant", "content": ...}`.
  - `perguntar(db, emp_id, usu_id, filtro, pergunta, historico, *, provedor=None, hoje=None) -> MetaAdsPerguntaResponse`:
    - Com `quantidade >= 30` no dia → `TooManyRequestsError("Limite de perguntas de hoje atingido.")`.
    - Mensagens: `system = PROMPT_PERGUNTA + "\n\nNúmeros do período (JSON):\n" + json(contexto)`, depois o histórico filtrado, depois a pergunta.
    - Só resposta bem-sucedida incrementa a contagem.
    - Falha da IA → `BadRequestError(f"{PREFIXO_AVISO}: {motivo}")`.
  - Rota `POST /api/meta-ads/cockpit/perguntar` (usuário da empresa; `usu_id = current_user.usuId`).

- [ ] **Step 1: Testes que falham**
  - `test_historico_filtrado`:
    - papel `system` é descartado;
    - texto de 2.001 caracteres é descartado;
    - com 20 mensagens válidas, ficam as 12 últimas;
    - a primeira mensagem enviada ao provedor é sempre o `system` do servidor, com o contexto.
  - `test_limite_diario`:
    - 30 respostas ok → a 31ª levanta `TooManyRequestsError`;
    - no dia seguinte (`hoje` + 1) volta a responder;
    - `restantesHoje` decresce até 0.
  - `test_falha_nao_conta`: provedor que levanta → `BadRequestError` e a contagem não muda.
  - `test_pergunta_sem_dados_pessoais`: o conteúdo enviado ao provedor não contém nome, telefone nem e-mail do lead.
  - `test_rota_pergunta_vazia_422`: `pergunta: "   "` → 422; pergunta com 501 caracteres → 422.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar** + suíte completa.
- [ ] **Step 5: Commit**: `Cockpit: perguntas ao analista com limite diário por usuário`.

---

### Task 7: Componentes visuais do cockpit

**Files:**
- Modify: `frontend/src/pages/Campanhas/metaAdsTipos.ts`, `frontend/src/styles.css`
- Create em `frontend/src/pages/Campanhas/cockpit/`: `SeloSaude.tsx`, `CartoesIndicadores.tsx`, `FunilCockpit.tsx`, `GraficosTendencia.tsx`, `MatrizCriativos.tsx`, `TabelaCriativos.tsx`, `SaudeOperacao.tsx`

**Interfaces:**
- Consumes: `MetaAdsCockpitResponse` da Task 4.
- Produces:
  - Tipos TS espelhando os schemas da Task 4 (`MetaAdsCockpit`, `CockpitEtapa`, `CockpitPonto`, `CockpitCriativo`, `CockpitSelo`, `CockpitQuadrante`).
  - `ROTULO_SELO` (`bom: "Bom"`, `atencao: "Atenção"`, `ruim: "Ruim"`, `sem_dados: "Sem dados"`) e `ROTULO_ETAPA` (rótulos do protótipo: "Viram o anúncio", "Clicaram", "Viraram lead", "Chegaram ao CRM", "Viraram MQL", "Oportunidade", "Contrato").
  - `intervaloUltimosDias(n: number): { inicio: string; fim: string }`: hoje e os n−1 dias anteriores.
  - Componentes, todos só de apresentação, recebendo `cockpit: MetaAdsCockpit`:
    - `CartoesIndicadores` também recebe `comparar: boolean`.
    - `MatrizCriativos` também recebe `metas`.

- [ ] **Step 1: `SeloSaude`**: etiqueta com o texto do selo e as cores do protótipo (bom `#ccfbf1`/`#134e4a`, atenção `#fef3c7`/`#78350f`, ruim `#fee2e2`/`#7f1d1d`, sem dados `#e2e8f0`/`#334155`).
- [ ] **Step 2: `CartoesIndicadores`**: os 8 cartões da spec 5.4, com rótulo, valor, selo (CPL, MQLs e custo por MQL), uma linha de comparação e a frase para leigo.
  - A linha de comparação é a variação contra o período anterior quando `comparar && anteriorTemDados`. Para custos, o texto diz "caiu"/"subiu" com o percentual. Quando `comparar && !anteriorTemDados`, a linha é "sem dados no período anterior" seguida da tendência; com `comparar` desligado, só a tendência.
  - Tendência do CPL: o CPL do primeiro e do último ponto da série com gasto.
  - Frases do protótipo.
- [ ] **Step 3: `FunilCockpit`**: sete degraus com larguras fixas decrescentes (100, 82, 64, 58, 34, 24, 14%), quantidade escrita na barra, taxa ("1,39% de quem viu" etc.) e custo. A etapa com `gargalo` fica destacada e o bloco "Maior perda" mostra `fraseGargalo`. Taxa > 100% ganha a dica "contagem por evento no período: inclui leads que entraram antes".
- [ ] **Step 4: `GraficosTendencia`**: dois SVG (`viewBox` responsivo, `width: 100%`).
  - Investimento em barras com o CPL em linha, e leads Meta x CRM em barras agrupadas.
  - Escala de 0 ao maior valor.
  - Cada barra e ponto é um elemento focável (`tabIndex=0`) com `<title>` mostrando o valor.
  - `aria-label` resume os valores.
  - Os dois gráficos ficam lado a lado em tela larga e empilham abaixo de 900px.
- [ ] **Step 5: `MatrizCriativos`**: área de 640×360 em `div` posicionado, com rolagem horizontal em tela estreita.
  - Eixo X: CPL de 0 ao maior entre o dobro da meta e o maior CPL.
  - Eixo Y: taxa de 0 ao maior entre o dobro da meta e a maior taxa, limitado a 100.
  - Bolha com diâmetro `14 + √investimento ÷ 1,6` px, na cor do quadrante.
  - Linhas tracejadas nas metas e rótulos dos quatro quadrantes, como no protótipo.
  - Ficam fora da matriz os `aguardar_dados`; anúncios sem lead Meta e com `pausar` vão numa faixa "sem lead" à direita.
  - "Amostra pequena" aparece como borda tracejada na bolha e é dita no `title`.
  - O bloco "Como ler" fica ao lado.
  - Pontos sobrepostos: deslocamento vertical de 8px por colisão.
- [ ] **Step 6: `TabelaCriativos`**: colunas da spec 5.8 (criativo, campanha, status, investido, leads, CPL, MQLs, taxa de MQL, recomendação, por quê), dentro de `campanhas-tabela-scroll`; a recomendação é uma etiqueta com texto.
- [ ] **Step 7: `SaudeOperacao`**: quatro cartões. "Alertas abertos" tem `<Link to="/monitoramento">` e "Origem a revisar" tem âncora `#revisao-origem`.
- [ ] **Step 8: Verificar**: tsc = 6; build OK.
- [ ] **Step 9: Commit**: `Cockpit: componentes de indicadores, funil, gráficos, matriz e tabela`.

---

### Task 8: Página Campanhas como cockpit

**Files:**
- Modify: `frontend/src/pages/Campanhas/CampanhasPage.tsx`, `frontend/src/styles.css`

**Interfaces:**
- Consumes: Task 7 (componentes), rotas `/meta-ads/cockpit` e `/meta-ads/painel`.

- [ ] **Step 1: Filtros**: botões "Últimos 30 dias", "Mês atual", "Ano atual" (padrão) e "Personalizado"; o último mostra De/Até + Aplicar. O atalho ativo leva `aria-pressed`. Ficam Conta e "Só campanhas ativas", e entra a caixa "Comparar com período anterior", ligada por padrão.
- [ ] **Step 2: Carga**: `/cockpit` e `/painel` com os mesmos parâmetros, em paralelo, com a guarda `ativo` contra resposta fora de ordem, Loader e `integracao-erro` próprios em cada um. O estado "sem conta" fica como hoje.
- [ ] **Step 3: Composição**, na ordem da spec:
  - espaço do cartão do analista (vazio até a Task 9);
  - `CartoesIndicadores`;
  - `FunilCockpit`;
  - `GraficosTendencia`;
  - `MatrizCriativos`;
  - `TabelaCriativos`;
  - `SaudeOperacao`;
  - título "Detalhe por campanha" com a tabela em árvore atual e a lista de revisão de origem (`id="revisao-origem"`) e o modal.

  Os 10 cartões antigos saem.
- [ ] **Step 4: Verificar**: tsc = 6; build OK; abrir a página no navegador com o backend local (se disponível) e conferir que os blocos empilham em ~400px.
- [ ] **Step 5: Commit**: `Campanhas: página vira o cockpit, com a tabela detalhada embaixo`.

---

### Task 9: Leitura do analista e chat na tela

**Files:**
- Create: `frontend/src/pages/Campanhas/cockpit/LeituraAnalista.tsx`, `frontend/src/pages/Campanhas/cockpit/PergunteAnalista.tsx`
- Modify: `frontend/src/pages/Campanhas/CampanhasPage.tsx`, `frontend/src/pages/Campanhas/metaAdsTipos.ts`, `frontend/src/styles.css`

**Interfaces:**
- Consumes: rotas da Task 5 e da Task 6.

- [ ] **Step 1: `LeituraAnalista`**: cartão escuro do protótipo (fundo `#0f172a`).
  - Sempre: `SeloSaude` com `selos.saude` e `fraseGargalo`.
  - Com leitura guardada: manchete e os três blocos ("O que funciona", "Onde está o problema", "O que olhar agora"), ou o `texto` cru. Ao lado vai "Gerada em dd/mm hh:mm"; com `desatualizada`, o aviso "gerada com números anteriores".
  - Botão "Gerar leitura" / "Gerar de novo", desabilitado enquanto gera e quando `iaDisponivel` é falso. Mostra `aviso` quando houver.
  - Recarrega pelo `GET` quando o recorte muda.
- [ ] **Step 2: `PergunteAnalista`**: as três perguntas sugeridas da spec 5.12, o campo "Sua pergunta" (máx. 500, contador) e o botão Enviar.
  - Lista as trocas da sessão e manda as 6 últimas trocas no `historico`.
  - Mostra "Restam N perguntas hoje".
  - Erro 429 → "Limite de perguntas de hoje atingido."; outros erros usam `mensagemErroApi`.
  - A conversa zera quando o recorte muda.
  - Sem `iaDisponivel`: o aviso no lugar do campo.
- [ ] **Step 3:** Encaixar os dois no topo da página (lado a lado, empilhando abaixo de 900px).
- [ ] **Step 4: Verificar**: tsc = 6; build OK.
- [ ] **Step 5: Commit**: `Cockpit: leitura do analista e Pergunte ao analista na tela`.

---

### Task 10: Implantação (controlador, com ok do Carlos em cada passo)

Executada pelo controlador da sessão, não por subagente.

- [ ] **Step 1: Suíte e build** no branch: backend completo OK; tsc = 6; build OK.
- [ ] **Step 2: Migrations** `0037`–`0039` no banco do `.env` (`.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head`), **só com ok do Carlos**, e conferência das colunas e tabelas.
- [ ] **Step 3: Conferência com dados reais**: chamar `cockpit.montar` para 01/06–26/10 (empresa 2) e conferir contra os números do protótipo:
  - investimento R$ 8.025,99; 42 leads Meta; 36 no CRM; 3 MQLs;
  - gargalo `mql`;
  - nenhum criativo em `escalar`.
- [ ] **Step 4: Documentação**:
  - `docs/META_ADS.md` ganha a seção "Cockpit": metas, quadrantes, leitura e limite do chat;
  - a spec passa a "implementada" e ganha a seção "Ajustes na implementação";
  - commit.

---

## Ajustes em relação à especificação

1. Anúncio sem lead da Meta mas com lead no CRM (a Meta às vezes não reporta o lead) usa os leads do CRM no CPL, em vez de cair na regra "sem lead". Senão um criativo com MQL poderia sair como "Pausar".
2. A rota do cockpit exige as duas datas (o frontend sempre manda).
3. O recorte da leitura guarda "todas as contas" como `mclMacId = 0`, porque um único com coluna nula não impede duplicatas no MySQL.
4. A ferramenta MCP `cockpit_campanhas` devolve exatamente o contexto enviado à IA.
5. `iaDisponivel` vem na resposta da leitura para a tela saber se mostra o chat.
