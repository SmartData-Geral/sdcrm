# Meta Ads — Campanhas, custo e retorno — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cada empresa conecta suas contas do Meta Ads (token de System User), o CRM sincroniza investimento e métricas por campanha × dia, liga os leads às campanhas e mostra custo por lead, custo por venda, MRR e retorno numa página "Campanhas", numa faixa do Dashboard e no detalhe do lead.

**Architecture:** Pacote `backend/services/meta_ads/` com cinco módulos de responsabilidade única (cliente da Graph API, vínculo lead→campanha, sincronização, contas, indicadores), cinco tabelas novas e duas colunas em `oportunidade`. A sync agendada roda num worker asyncio no lifespan (modelo do `webhook_worker`); a sync manual roda em `BackgroundTasks` do FastAPI. Os indicadores reaproveitam as condições de período e as expressões de MRR/Projeto do `crm_dashboard_service`, para os números baterem com a aba Fontes.

**Tech Stack:** Python 3.11 (Docker) / 3.14 (local), FastAPI 0.135.2, SQLAlchemy 2.0.48, Alembic 1.13.2, httpx 0.28.1, cryptography 46.0.6 (Fernet), `unittest` + SQLite em memória; React 18 + TypeScript + Vite, sem biblioteca de gráficos.

**Spec:** `docs/superpowers/specs/2026-10-14-meta-ads-campanhas-design.md`

## Global Constraints

- Tabelas e colunas no padrão `<alias><Campo>` (`docs/DATABASE_GUIDELINES.md`). Aliases: `meta_ads_conta`→`mac`, `meta_ads_conta_origem`→`mco`, `meta_ads_campanha`→`mcg`, `meta_ads_insight_diario`→`mid`, `meta_ads_sync_log`→`msl`.
- Toda consulta e gravação filtra pela empresa do header `X-Company-Id`; sem empresa: `BadRequestError("Selecione uma empresa")`.
- Rotas de configuração (contas, testar, sincronizar, logs) exigem `require_admin`; rotas de leitura (painel, resumo, detalhe, opções, vínculo manual) exigem só `require_user_in_company`.
- O token do Meta nunca sai pela API, nunca vai em URL (cabeçalho `Authorization: Bearer`) e nunca aparece em log ou mensagem; gravado com `core/cripto.cifrar` (prefixo `enc:v1:`).
- Retorno = `(MRR × 12 + Projeto) ÷ Investimento`. Divisão por zero devolve `None` (exibido "—").
- Janela da sync: 30 dias; carga inicial: 90 dias; reprocessar período: máx. 366 dias; trava de sync considerada morta após 30 min.
- Retentativas em erro temporário do Meta: esperas de 30s, 60s, 120s (3 novas tentativas).
- Tipos de ação contados como lead, em ordem de prioridade (conta só o primeiro presente): `lead`, `onsite_conversion.lead_grouped`, `offsite_conversion.fb_pixel_lead`.
- Mensagens de erro e textos de tela em português.
- Testes backend: `unittest`, da raiz do repo: `.venv/Scripts/python -m unittest backend.tests.<modulo> -v`. Testes que precisam de SQL usam `backend/tests/banco_sqlite.py` (Task 2).
- Frontend não tem testes automatizados: a verificação é `npx tsc --noEmit -p .` em `frontend/` sem erro novo (a base tem **6 erros pré-existentes** em `OportunidadeDetalhePage.tsx` e `OportunidadesPage.tsx`; o total deve continuar 6) e `npm run build`.
- **Nunca rodar `alembic upgrade` contra o banco do `.env` local sem o Carlos confirmar**: ele aponta para um banco com dados reais.
- Commits pequenos, um por task, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Ajustes em relação à especificação

1. **Status `token_invalido` e coluna `macSyncIniciadaEm`.** A spec usa `erro` para token inválido e diz que a agendada "pula a conta até trocar o token" — sem um status próprio não há como distinguir token inválido de erro comum (que deve tentar de novo no dia seguinte). `macSyncIniciadaEm` guarda quando a trava foi pega, para liberar travas mortas após 30 min.
2. **Sync manual em `BackgroundTasks`.** O worker cuida só da rodada diária; o clique em "Sincronizar agora" pega a trava na própria requisição (409 se ocupada) e roda a sync após a resposta. Mesmo efeito da spec, sem fila em memória.
3. **Vínculo manual em rota própria** `PATCH /api/meta-ads/oportunidades/{opo_id}/campanha`, e não no `PUT /api/oportunidades/{id}` (a tela de detalhe envia o formulário inteiro no PUT; misturar quebraria a marca de "manual").
4. **MRR/Projeto com a regra da aba Fontes.** A spec diz "somados sobre as vendas"; a aba Fontes soma o MRR das ganhas **recebidas ou fechadas** no período. Para cumprir o critério de sucesso 4 (números batendo), as condições de período viram um helper compartilhado `condicoes_periodo` no `crm_dashboard_service`.
5. **Integrações → página própria** `/integracoes/meta-ads` (o menu Integrações usa páginas, não abas).
6. **Alcance** é gravado mas não exibido: alcance diário não é somável.
7. **Origem no log:** `agendada`, `manual`, `periodo`, `carga_inicial`.
8. **Detalhe da campanha em `Modal`** (componente existente) em vez de painel lateral.
9. **Rota extra** `GET /api/meta-ads/contas-opcoes` (não admin), para o filtro de conta da página Campanhas.

A spec é atualizada na Task 12.

## Review Focus

1. **Token colado com espaços ou quebra de linha** (copiado do Business Manager) — deve ser gravado sem os espaços e funcionar (teste na Task 7: `test_token_e_normalizado`).
2. **Campanha renomeada no Meta depois de leads já ligados** — o nome é atualizado e os leads continuam ligados pela chave interna (teste na Task 5: `test_renomear_campanha_mantem_vinculo`).
3. **Mesmo nome de campanha em duas contas da mesma empresa** — ambíguo, o lead não é ligado a nenhuma (teste na Task 4: `test_nome_ambiguo_nao_liga`).
4. **Período sem gasto e sem lead** (conta recém-conectada ou período futuro) — painel com total zerado e indicadores "—", sem erro de divisão (teste na Task 8: `test_periodo_vazio`).
5. **"Sincronizar agora" clicado duas vezes seguidas** — a segunda resposta é 409 "já em andamento" e nada é duplicado (teste na Task 7: `test_sincronizar_duas_vezes_da_409`).

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `backend/requirements.txt` | Modificar | Fixar `cryptography`. |
| `backend/config.py` | Modificar | `SECRETS_ENCRYPTION_KEY`, `META_API_VERSION`, `META_ADS_SYNC_ENABLED`, `META_ADS_SYNC_HORA`. |
| `.env.example` | Modificar | Documentar as variáveis novas. |
| `backend/core/cripto.py` | Criar | `cifrar` / `decifrar` (Fernet). |
| `backend/models/meta_ads_conta.py` | Criar | Model + constantes de status. |
| `backend/models/meta_ads_conta_origem.py` | Criar | Origens que contam como Meta. |
| `backend/models/meta_ads_campanha.py` | Criar | Campanhas sincronizadas. |
| `backend/models/meta_ads_insight_diario.py` | Criar | Métricas campanha × dia. |
| `backend/models/meta_ads_sync_log.py` | Criar | Auditoria das execuções. |
| `backend/models/oportunidade.py` | Modificar | `opoMcgId`, `opoMcgManual`. |
| `backend/models/__init__.py` | Modificar | Registrar os models. |
| `backend/alembic/versions/0030_meta_ads.py` | Criar | Migration. |
| `backend/schemas/oportunidade.py` | Modificar | Expor `opoMcgId`, `opoMcgManual` na resposta. |
| `backend/schemas/meta_ads.py` | Criar | Schemas da API. |
| `backend/services/meta_ads/__init__.py` | Criar | Pacote. |
| `backend/services/meta_ads/cliente_graph.py` | Criar | HTTP com a Graph API, erros, retentativas, paginação. |
| `backend/services/meta_ads/vinculo.py` | Criar | Lead → campanha. |
| `backend/services/meta_ads/sincronizacao.py` | Criar | Trava, janela, gravação, log. |
| `backend/services/meta_ads/contas.py` | Criar | CRUD de contas, teste de conexão, logs. |
| `backend/services/meta_ads/indicadores.py` | Criar | Painel, detalhe, resumo, opções, vínculo manual. |
| `backend/services/crm_dashboard_service.py` | Modificar | Extrair `condicoes_periodo`. |
| `backend/services/lead_intake_service.py` | Modificar | Chamar o vínculo ao criar/atualizar lead. |
| `backend/workers/meta_ads_worker.py` | Criar | Rodada diária. |
| `backend/routers/meta_ads_router.py` | Criar | Rotas `/api/meta-ads/*`. |
| `backend/main.py` | Modificar | Lifespan + router. |
| `backend/tests/banco_sqlite.py` | Criar | SQLite em memória + fábricas. |
| `backend/tests/test_core_cripto.py` | Criar | |
| `backend/tests/test_meta_ads_modelos.py` | Criar | |
| `backend/tests/test_meta_ads_cliente_graph.py` | Criar | |
| `backend/tests/test_meta_ads_vinculo.py` | Criar | |
| `backend/tests/test_meta_ads_sincronizacao.py` | Criar | |
| `backend/tests/test_meta_ads_worker.py` | Criar | |
| `backend/tests/test_meta_ads_contas.py` | Criar | |
| `backend/tests/test_meta_ads_router.py` | Criar | |
| `backend/tests/test_meta_ads_indicadores.py` | Criar | |
| `frontend/src/pages/Campanhas/metaAdsTipos.ts` | Criar | Tipos e formatadores compartilhados. |
| `frontend/src/pages/Integracoes/MetaAdsContasPage.tsx` | Criar | Configuração das contas (admin). |
| `frontend/src/pages/Campanhas/CampanhasPage.tsx` | Criar | Página Campanhas. |
| `frontend/src/pages/Campanhas/CampanhaDetalheModal.tsx` | Criar | Detalhe com gráfico diário e leads. |
| `frontend/src/components/metaAds/MetaAdsResumoFaixa.tsx` | Criar | Faixa do Dashboard. |
| `frontend/src/components/metaAds/CampanhaMetaField.tsx` | Criar | Campo no detalhe do lead. |
| `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx` | Modificar | Rotas e menu. |
| `frontend/src/pages/Dashboard/DashboardPage.tsx` | Modificar | Inserir a faixa. |
| `frontend/src/pages/Oportunidades/OportunidadeDetalhePage.tsx` | Modificar | Inserir o campo. |
| `frontend/src/styles.css` | Modificar | Estilos da página e da faixa. |
| `docs/META_ADS.md` | Criar | Como gerar o token e conectar. |

---

### Task 1: Configuração e criptografia de segredos

**Files:**
- Modify: `backend/requirements.txt`, `backend/config.py`, `.env.example`
- Create: `backend/core/cripto.py`
- Test: `backend/tests/test_core_cripto.py`

**Interfaces:**
- Produces: `backend.core.cripto.cifrar(texto: str) -> str`, `backend.core.cripto.decifrar(valor: str | None) -> str | None`, `backend.core.cripto.PREFIXO = "enc:v1:"`; settings `SECRETS_ENCRYPTION_KEY: str | None`, `META_API_VERSION: str`, `META_ADS_SYNC_ENABLED: bool`, `META_ADS_SYNC_HORA: int`.

- [ ] **Step 1: Write the failing test** — `backend/tests/test_core_cripto.py`

```python
import unittest

from backend.core import cripto


class CriptoTests(unittest.TestCase):
    def test_ida_e_volta(self) -> None:
        cifrado = cripto.cifrar("EAAB-segredo-123")
        self.assertTrue(cifrado.startswith(cripto.PREFIXO))
        self.assertNotIn("segredo", cifrado)
        self.assertEqual(cripto.decifrar(cifrado), "EAAB-segredo-123")

    def test_cifras_diferentes_para_o_mesmo_texto(self) -> None:
        self.assertNotEqual(cripto.cifrar("abc"), cripto.cifrar("abc"))

    def test_chave_trocada_devolve_none(self) -> None:
        cifrado = cripto.cifrar("EAAB-segredo-123")
        original = cripto.settings.SECRETS_ENCRYPTION_KEY
        try:
            cripto.settings.SECRETS_ENCRYPTION_KEY = "outra-chave-bem-diferente"
            self.assertIsNone(cripto.decifrar(cifrado))
        finally:
            cripto.settings.SECRETS_ENCRYPTION_KEY = original

    def test_valor_invalido_devolve_none(self) -> None:
        for valor in (None, "", "texto-puro", "enc:v1:lixo"):
            self.assertIsNone(cripto.decifrar(valor), valor)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m unittest backend.tests.test_core_cripto -v`
Expected: FAIL com `ImportError: cannot import name 'cripto'`.

- [ ] **Step 3: Implementar**

`backend/core/cripto.py`:

```python
"""
Cifra simetrica (Fernet) para segredos guardados no banco, como o token do Meta Ads.

Formato gravado: "enc:v1:<token Fernet>". A chave e o SHA-256 de SECRETS_ENCRYPTION_KEY,
ou do JWT_SECRET_KEY quando a primeira nao esta definida (mesmo modelo do Adverse).
Trocar a semente torna os valores gravados ilegiveis: decifrar devolve None e quem chama
trata como "token precisa ser cadastrado de novo".
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings

PREFIXO = "enc:v1:"


def _fernet() -> Fernet:
    semente = settings.SECRETS_ENCRYPTION_KEY or settings.JWT_SECRET_KEY
    chave = base64.urlsafe_b64encode(hashlib.sha256(semente.encode("utf-8")).digest())
    return Fernet(chave)


def cifrar(texto: str) -> str:
    return PREFIXO + _fernet().encrypt(texto.encode("utf-8")).decode("ascii")


def decifrar(valor: str | None) -> str | None:
    """Texto puro, ou None se o valor nao for legivel (formato invalido ou chave trocada)."""
    if not valor or not valor.startswith(PREFIXO):
        return None
    try:
        return _fernet().decrypt(valor[len(PREFIXO):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None
```

Em `backend/config.py`, logo depois de `WEBHOOK_CLAIM_TIMEOUT_MINUTOS`:

```python

    # --- Meta Ads ---
    # Semente da cifra de segredos gravados no banco (tokens do Meta). Vazio = usa o
    # JWT_SECRET_KEY. ATENCAO: trocar este valor torna os tokens gravados ilegiveis.
    SECRETS_ENCRYPTION_KEY: str | None = None
    # Versao da Graph API. Conferir a versao estavel vigente em
    # https://developers.facebook.com/docs/graph-api/changelog antes de subir.
    META_API_VERSION: str = "v24.0"
    # Desligavel nas replicas de API se um dia houver um container de worker dedicado.
    META_ADS_SYNC_ENABLED: bool = True
    # Hora (0-23, America/Sao_Paulo) da sincronizacao diaria.
    META_ADS_SYNC_HORA: int = Field(default=4, ge=0, le=23)
```

Em `backend/requirements.txt`, depois de `httpx==0.28.1`:

```
# Fernet para cifrar o token do Meta Ads no banco. Ja vinha via python-jose[cryptography];
# fixado aqui porque passamos a depender dele diretamente.
cryptography==46.0.6
```

No fim de `.env.example`:

```

# --- Meta Ads ---
# Semente da cifra dos tokens do Meta gravados no banco. Vazio = usa JWT_SECRET_KEY.
# ATENCAO: trocar torna os tokens gravados ilegiveis (precisam ser cadastrados de novo).
SECRETS_ENCRYPTION_KEY=
META_API_VERSION=v24.0
META_ADS_SYNC_ENABLED=true
# Hora da sincronizacao diaria (0-23, horario de Brasilia).
META_ADS_SYNC_HORA=4
```

- [ ] **Step 4: Conferir a versão da Graph API**

Abrir https://developers.facebook.com/docs/graph-api/changelog e confirmar a última versão estável. Se for diferente de `v24.0`, trocar o padrão em `config.py` e em `.env.example`.

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python -m unittest backend.tests.test_core_cripto -v`
Expected: 4 testes OK.

- [ ] **Step 6: Commit**

```bash
git add backend/core/cripto.py backend/tests/test_core_cripto.py backend/config.py backend/requirements.txt .env.example
git commit -m "Meta Ads: configuração e cifra de segredos (Fernet)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Models, migration e banco de teste

**Files:**
- Create: `backend/models/meta_ads_conta.py`, `backend/models/meta_ads_conta_origem.py`, `backend/models/meta_ads_campanha.py`, `backend/models/meta_ads_insight_diario.py`, `backend/models/meta_ads_sync_log.py`, `backend/alembic/versions/0030_meta_ads.py`, `backend/tests/banco_sqlite.py`
- Modify: `backend/models/oportunidade.py` (depois de `opoOpoAnteriorId`), `backend/models/__init__.py`, `backend/schemas/oportunidade.py:89-98`
- Test: `backend/tests/test_meta_ads_modelos.py`

**Interfaces:**
- Consumes: `cripto.cifrar` (Task 1).
- Produces: classes `MetaAdsConta`, `MetaAdsContaOrigem`, `MetaAdsCampanha`, `MetaAdsInsightDiario`, `MetaAdsSyncLog`; constantes em `backend.models.meta_ads_conta`: `STATUS_PENDENTE="pendente"`, `STATUS_SINCRONIZANDO="sincronizando"`, `STATUS_OK="ok"`, `STATUS_AVISO="aviso"`, `STATUS_ERRO="erro"`, `STATUS_TOKEN_INVALIDO="token_invalido"`; colunas `Oportunidade.opoMcgId: int | None`, `Oportunidade.opoMcgManual: bool`; fábricas de teste em `backend.tests.banco_sqlite`: `nova_sessao() -> Session`, `criar_empresa(db, nome="Acme") -> Empresa`, `criar_origem(db, emp_id, nome) -> ComoConheceu`, `criar_oportunidade(db, emp_id, **campos) -> Oportunidade`, `criar_conta(db, emp_id, *, act="act_111", nome="Conta", token="EAAB-token-de-teste-1234", origens=()) -> MetaAdsConta`, `criar_campanha(db, conta, externa, nome, status="ACTIVE") -> MetaAdsCampanha`, `criar_insight(db, campanha, dia, investimento, *, impressoes=1000, cliques=50, leads=0) -> MetaAdsInsightDiario`.

- [ ] **Step 1: Criar os models**

`backend/models/meta_ads_conta.py`:

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base

STATUS_PENDENTE = "pendente"
STATUS_SINCRONIZANDO = "sincronizando"
STATUS_OK = "ok"
STATUS_AVISO = "aviso"
STATUS_ERRO = "erro"
# Separado de "erro" porque a rodada diaria pula estas contas ate alguem trocar o token.
STATUS_TOKEN_INVALIDO = "token_invalido"


class MetaAdsConta(Base):
    """
    Conta de anuncios do Meta conectada por uma empresa.

    macToken guarda o token do System User cifrado (core/cripto). Ele nunca sai pela API:
    a tela mostra so macTokenFinal ("....1234").
    """

    __tablename__ = "meta_ads_conta"
    __table_args__ = (
        UniqueConstraint("macEmpId", "macContaExterna", name="uq_meta_ads_conta_emp_ext"),
    )

    macId: Mapped[int] = IdColumnFactory.int_id("macId")
    macEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False, index=True
    )
    macNome: Mapped[str] = mapped_column(String(150), nullable=False)
    macContaExterna: Mapped[str] = mapped_column(String(40), nullable=False)
    macToken: Mapped[str] = mapped_column(Text, nullable=False)
    macTokenFinal: Mapped[str] = mapped_column(String(4), nullable=False)
    macMoeda: Mapped[str | None] = mapped_column(String(3), nullable=True)
    macFuso: Mapped[str | None] = mapped_column(String(60), nullable=True)
    macStatus: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_PENDENTE)
    macMensagem: Mapped[str | None] = mapped_column(String(500), nullable=True)
    macUltimaSync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Quando a trava de sincronizacao foi pega; trava com mais de 30 min e considerada morta.
    macSyncIniciadaEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    macCargaInicialFeita: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    macAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("macAtivo")
    macDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("macDataCriacao")
    macDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao(
        "macDataAtualizacao"
    )
```

`backend/models/meta_ads_conta_origem.py`:

```python
from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..database import Base


class MetaAdsContaOrigem(Base):
    """Origem ("Como conheceu") cujos leads contam como vindos daquela conta do Meta."""

    __tablename__ = "meta_ads_conta_origem"
    __table_args__ = (UniqueConstraint("mcoMacId", "mcoCcoId", name="uq_meta_ads_conta_origem"),)

    mcoId: Mapped[int] = IdColumnFactory.int_id("mcoId")
    mcoMacId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conta.macId", ondelete="CASCADE"), nullable=False, index=True
    )
    mcoCcoId: Mapped[int] = mapped_column(
        Integer, ForeignKey("como_conheceu.ccoId", ondelete="CASCADE"), nullable=False, index=True
    )
```

`backend/models/meta_ads_campanha.py`:

```python
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AuditColumnFactory, IdColumnFactory
from ..database import Base


class MetaAdsCampanha(Base):
    """Campanha sincronizada do Meta. O nome e atualizado a cada sync (pode mudar no Meta)."""

    __tablename__ = "meta_ads_campanha"
    __table_args__ = (
        UniqueConstraint("mcgMacId", "mcgCampanhaExterna", name="uq_meta_ads_campanha_conta_ext"),
        Index("ix_meta_ads_campanha_emp_nome", "mcgEmpId", "mcgNomeNormalizado"),
    )

    mcgId: Mapped[int] = IdColumnFactory.int_id("mcgId")
    mcgEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False, index=True
    )
    mcgMacId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conta.macId", ondelete="CASCADE"), nullable=False, index=True
    )
    mcgCampanhaExterna: Mapped[str] = mapped_column(String(40), nullable=False)
    mcgNome: Mapped[str] = mapped_column(String(400), nullable=False)
    mcgNomeNormalizado: Mapped[str] = mapped_column(String(400), nullable=False)
    mcgObjetivo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    mcgStatus: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mcgDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("mcgDataCriacao")
    mcgDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao(
        "mcgDataAtualizacao"
    )
```

`backend/models/meta_ads_insight_diario.py`:

```python
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..database import Base


class MetaAdsInsightDiario(Base):
    """Metricas de uma campanha num dia (fuso da conta). Regravado a cada sync do periodo."""

    __tablename__ = "meta_ads_insight_diario"
    __table_args__ = (
        UniqueConstraint("midMcgId", "midData", name="uq_meta_ads_insight_campanha_dia"),
        Index("ix_meta_ads_insight_emp_data", "midEmpId", "midData"),
    )

    midId: Mapped[int] = IdColumnFactory.int_id("midId")
    midEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False
    )
    midMacId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conta.macId", ondelete="CASCADE"), nullable=False, index=True
    )
    midMcgId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_campanha.mcgId", ondelete="CASCADE"), nullable=False
    )
    midData: Mapped[date] = mapped_column(Date, nullable=False)
    midInvestimento: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    midImpressoes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    midCliques: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Gravado mas nao exibido: alcance diario nao e somavel entre dias.
    midAlcance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    midLeadsMeta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

`backend/models/meta_ads_sync_log.py`:

```python
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..core.tempo import utcnow
from ..database import Base


class MetaAdsSyncLog(Base):
    """Uma execucao de sincronizacao de uma conta. Origem: agendada|manual|periodo|carga_inicial."""

    __tablename__ = "meta_ads_sync_log"

    mslId: Mapped[int] = IdColumnFactory.int_id("mslId")
    mslMacId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conta.macId", ondelete="CASCADE"), nullable=False, index=True
    )
    mslInicio: Mapped[date] = mapped_column(Date, nullable=False)
    mslFim: Mapped[date] = mapped_column(Date, nullable=False)
    mslOrigem: Mapped[str] = mapped_column(String(20), nullable=False)
    mslStatus: Mapped[str] = mapped_column(String(20), nullable=False)
    mslLinhas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mslLeadsVinculados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mslErro: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mslDuracaoMs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mslDataExecucao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
```

Em `backend/models/oportunidade.py`, logo depois do bloco de `opoOpoAnteriorId` (antes de `opoAtivo`):

```python
    # Campanha do Meta Ads ligada ao lead (services/meta_ads/vinculo.py).
    opoMcgId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("meta_ads_campanha.mcgId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # True quando um usuario escolheu a campanha (ou "nenhuma") na tela; o vinculo
    # automatico nunca mexe nessas oportunidades.
    opoMcgManual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

No fim de `backend/models/__init__.py`:

```python
from .meta_ads_conta import MetaAdsConta  # noqa: F401
from .meta_ads_conta_origem import MetaAdsContaOrigem  # noqa: F401
from .meta_ads_campanha import MetaAdsCampanha  # noqa: F401
from .meta_ads_insight_diario import MetaAdsInsightDiario  # noqa: F401
from .meta_ads_sync_log import MetaAdsSyncLog  # noqa: F401
```

Em `backend/schemas/oportunidade.py`, na classe `OportunidadeInDBBase`, depois de `opoDataAtualizacao`:

```python
    opoMcgId: int | None = None
    opoMcgManual: bool = False
```

- [ ] **Step 2: Criar o banco de teste** — `backend/tests/banco_sqlite.py`

```python
"""
Banco SQLite em memoria com o schema completo, para testes de servico que precisam de SQL
de verdade (sincronizacao, vinculo, indicadores). Os demais testes seguem com mocks.
"""

import os

os.environ.setdefault("API_KEY_PEPPER", "pepper-de-teste")

from datetime import date  # noqa: E402

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import backend.models  # noqa: E402,F401  (registra todas as tabelas no metadata)
from backend.core.cripto import cifrar  # noqa: E402
from backend.database import Base  # noqa: E402
from backend.models.como_conheceu import ComoConheceu  # noqa: E402
from backend.models.empresa import Empresa  # noqa: E402
from backend.models.meta_ads_campanha import MetaAdsCampanha  # noqa: E402
from backend.models.meta_ads_conta import MetaAdsConta  # noqa: E402
from backend.models.meta_ads_conta_origem import MetaAdsContaOrigem  # noqa: E402
from backend.models.meta_ads_insight_diario import MetaAdsInsightDiario  # noqa: E402
from backend.models.oportunidade import Oportunidade  # noqa: E402


def nova_sessao() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _ligar_fks(conexao, _registro):
        conexao.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    # Mesmas opcoes do SessionLocal de producao (expire_on_commit padrao = True).
    return sessionmaker(bind=engine, autoflush=False)()


def criar_empresa(db: Session, nome: str = "Acme") -> Empresa:
    emp = Empresa(empNome=nome)
    db.add(emp)
    db.commit()
    return emp


def criar_origem(db: Session, emp_id: int, nome: str) -> ComoConheceu:
    cco = ComoConheceu(ccoEmpId=emp_id, ccoNome=nome)
    db.add(cco)
    db.commit()
    return cco


def criar_oportunidade(db: Session, emp_id: int, **campos) -> Oportunidade:
    base = dict(opoEmpId=emp_id, opoTitulo="Lead", opoDataRecebimento=date(2026, 10, 1))
    base.update(campos)
    opo = Oportunidade(**base)
    db.add(opo)
    db.commit()
    return opo


def criar_conta(
    db: Session,
    emp_id: int,
    *,
    act: str = "act_111",
    nome: str = "Conta",
    token: str = "EAAB-token-de-teste-1234",
    origens=(),
) -> MetaAdsConta:
    conta = MetaAdsConta(
        macEmpId=emp_id,
        macNome=nome,
        macContaExterna=act,
        macToken=cifrar(token),
        macTokenFinal=token[-4:],
    )
    db.add(conta)
    db.flush()
    for cco_id in origens:
        db.add(MetaAdsContaOrigem(mcoMacId=conta.macId, mcoCcoId=cco_id))
    db.commit()
    return conta


def criar_campanha(
    db: Session, conta: MetaAdsConta, externa: str, nome: str, status: str = "ACTIVE"
) -> MetaAdsCampanha:
    camp = MetaAdsCampanha(
        mcgEmpId=conta.macEmpId,
        mcgMacId=conta.macId,
        mcgCampanhaExterna=externa,
        mcgNome=nome,
        mcgNomeNormalizado=" ".join(nome.split()).lower(),
        mcgStatus=status,
    )
    db.add(camp)
    db.commit()
    return camp


def criar_insight(
    db: Session,
    campanha: MetaAdsCampanha,
    dia: date,
    investimento: float,
    *,
    impressoes: int = 1000,
    cliques: int = 50,
    leads: int = 0,
) -> MetaAdsInsightDiario:
    linha = MetaAdsInsightDiario(
        midEmpId=campanha.mcgEmpId,
        midMacId=campanha.mcgMacId,
        midMcgId=campanha.mcgId,
        midData=dia,
        midInvestimento=investimento,
        midImpressoes=impressoes,
        midCliques=cliques,
        midAlcance=0,
        midLeadsMeta=leads,
    )
    db.add(linha)
    db.commit()
    return linha
```

- [ ] **Step 3: Write the failing test** — `backend/tests/test_meta_ads_modelos.py`

```python
import unittest
from datetime import date

from sqlalchemy.exc import IntegrityError

from backend.tests import banco_sqlite as b


class ModelosMetaAdsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)

    def test_conta_duplicada_na_mesma_empresa_e_recusada(self) -> None:
        b.criar_conta(self.db, self.emp.empId, act="act_1")
        with self.assertRaises(IntegrityError):
            b.criar_conta(self.db, self.emp.empId, act="act_1")

    def test_mesma_conta_em_empresas_diferentes_e_permitida(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        b.criar_conta(self.db, self.emp.empId, act="act_1")
        b.criar_conta(self.db, outra.empId, act="act_1")

    def test_insight_duplicado_no_mesmo_dia_e_recusado(self) -> None:
        conta = b.criar_conta(self.db, self.emp.empId)
        camp = b.criar_campanha(self.db, conta, "c1", "Campanha 1")
        b.criar_insight(self.db, camp, date(2026, 10, 1), 10)
        with self.assertRaises(IntegrityError):
            b.criar_insight(self.db, camp, date(2026, 10, 1), 20)

    def test_apagar_campanha_desliga_a_oportunidade(self) -> None:
        conta = b.criar_conta(self.db, self.emp.empId)
        camp = b.criar_campanha(self.db, conta, "c1", "Campanha 1")
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoMcgId=camp.mcgId)
        self.db.delete(camp)
        self.db.commit()
        self.db.refresh(opo)
        self.assertIsNone(opo.opoMcgId)
        self.assertFalse(opo.opoMcgManual)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run test**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_modelos -v`
Expected: 4 testes OK (models e fábricas já existem dos Steps 1–2; se algum falhar, corrigir o model antes de seguir).

- [ ] **Step 5: Criar a migration** — `backend/alembic/versions/0030_meta_ads.py`

```python
"""Meta Ads: contas, origens, campanhas, insights diarios, log e vinculo na oportunidade

Revision ID: 0030_meta_ads
Revises: 0029_crm_meta_valor_projeto
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0030_meta_ads"
down_revision: str | None = "0029_crm_meta_valor_projeto"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTA = "meta_ads_conta"
ORIGEM = "meta_ads_conta_origem"
CAMPANHA = "meta_ads_campanha"
INSIGHT = "meta_ads_insight_diario"
LOG = "meta_ads_sync_log"


def _tabelas(bind) -> set[str]:
    return set(inspect(bind).get_table_names())


def _indices(bind, tabela) -> set[str]:
    try:
        return {i["name"] for i in inspect(bind).get_indexes(tabela)}
    except Exception:
        return set()


def _criar_indices(bind, tabela, indices) -> None:
    existentes = _indices(bind, tabela)
    for nome, colunas in indices:
        if nome not in existentes:
            op.create_index(nome, tabela, colunas)


def upgrade() -> None:
    bind = op.get_bind()

    if CONTA not in _tabelas(bind):
        op.create_table(
            CONTA,
            sa.Column("macId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("macEmpId", sa.Integer(), nullable=False),
            sa.Column("macNome", sa.String(length=150), nullable=False),
            sa.Column("macContaExterna", sa.String(length=40), nullable=False),
            sa.Column("macToken", sa.Text(), nullable=False),
            sa.Column("macTokenFinal", sa.String(length=4), nullable=False),
            sa.Column("macMoeda", sa.String(length=3), nullable=True),
            sa.Column("macFuso", sa.String(length=60), nullable=True),
            sa.Column("macStatus", sa.String(length=20), nullable=False, server_default="pendente"),
            sa.Column("macMensagem", sa.String(length=500), nullable=True),
            sa.Column("macUltimaSync", sa.DateTime(timezone=True), nullable=True),
            sa.Column("macSyncIniciadaEm", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "macCargaInicialFeita", sa.Boolean(), nullable=False, server_default=sa.text("0")
            ),
            sa.Column("macAtivo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("macDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.Column("macDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("macId"),
            sa.ForeignKeyConstraint(["macEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.UniqueConstraint("macEmpId", "macContaExterna", name="uq_meta_ads_conta_emp_ext"),
        )
    _criar_indices(bind, CONTA, [("ix_meta_ads_conta_macEmpId", ["macEmpId"])])

    if ORIGEM not in _tabelas(bind):
        op.create_table(
            ORIGEM,
            sa.Column("mcoId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("mcoMacId", sa.Integer(), nullable=False),
            sa.Column("mcoCcoId", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("mcoId"),
            sa.ForeignKeyConstraint(["mcoMacId"], ["meta_ads_conta.macId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["mcoCcoId"], ["como_conheceu.ccoId"], ondelete="CASCADE"),
            sa.UniqueConstraint("mcoMacId", "mcoCcoId", name="uq_meta_ads_conta_origem"),
        )
    _criar_indices(
        bind,
        ORIGEM,
        [
            ("ix_meta_ads_conta_origem_mcoMacId", ["mcoMacId"]),
            ("ix_meta_ads_conta_origem_mcoCcoId", ["mcoCcoId"]),
        ],
    )

    if CAMPANHA not in _tabelas(bind):
        op.create_table(
            CAMPANHA,
            sa.Column("mcgId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("mcgEmpId", sa.Integer(), nullable=False),
            sa.Column("mcgMacId", sa.Integer(), nullable=False),
            sa.Column("mcgCampanhaExterna", sa.String(length=40), nullable=False),
            sa.Column("mcgNome", sa.String(length=400), nullable=False),
            sa.Column("mcgNomeNormalizado", sa.String(length=400), nullable=False),
            sa.Column("mcgObjetivo", sa.String(length=60), nullable=True),
            sa.Column("mcgStatus", sa.String(length=30), nullable=True),
            sa.Column("mcgDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.Column("mcgDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("mcgId"),
            sa.ForeignKeyConstraint(["mcgEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["mcgMacId"], ["meta_ads_conta.macId"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "mcgMacId", "mcgCampanhaExterna", name="uq_meta_ads_campanha_conta_ext"
            ),
        )
    _criar_indices(
        bind,
        CAMPANHA,
        [
            ("ix_meta_ads_campanha_mcgEmpId", ["mcgEmpId"]),
            ("ix_meta_ads_campanha_mcgMacId", ["mcgMacId"]),
            ("ix_meta_ads_campanha_emp_nome", ["mcgEmpId", "mcgNomeNormalizado"]),
        ],
    )

    if INSIGHT not in _tabelas(bind):
        op.create_table(
            INSIGHT,
            sa.Column("midId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("midEmpId", sa.Integer(), nullable=False),
            sa.Column("midMacId", sa.Integer(), nullable=False),
            sa.Column("midMcgId", sa.Integer(), nullable=False),
            sa.Column("midData", sa.Date(), nullable=False),
            sa.Column(
                "midInvestimento", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")
            ),
            sa.Column("midImpressoes", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("midCliques", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("midAlcance", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("midLeadsMeta", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.PrimaryKeyConstraint("midId"),
            sa.ForeignKeyConstraint(["midEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["midMacId"], ["meta_ads_conta.macId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["midMcgId"], ["meta_ads_campanha.mcgId"], ondelete="CASCADE"),
            sa.UniqueConstraint("midMcgId", "midData", name="uq_meta_ads_insight_campanha_dia"),
        )
    _criar_indices(
        bind,
        INSIGHT,
        [
            ("ix_meta_ads_insight_emp_data", ["midEmpId", "midData"]),
            ("ix_meta_ads_insight_diario_midMacId", ["midMacId"]),
        ],
    )

    if LOG not in _tabelas(bind):
        op.create_table(
            LOG,
            sa.Column("mslId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("mslMacId", sa.Integer(), nullable=False),
            sa.Column("mslInicio", sa.Date(), nullable=False),
            sa.Column("mslFim", sa.Date(), nullable=False),
            sa.Column("mslOrigem", sa.String(length=20), nullable=False),
            sa.Column("mslStatus", sa.String(length=20), nullable=False),
            sa.Column("mslLinhas", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column(
                "mslLeadsVinculados", sa.Integer(), nullable=False, server_default=sa.text("0")
            ),
            sa.Column("mslErro", sa.String(length=500), nullable=True),
            sa.Column("mslDuracaoMs", sa.Integer(), nullable=True),
            sa.Column("mslDataExecucao", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("mslId"),
            sa.ForeignKeyConstraint(["mslMacId"], ["meta_ads_conta.macId"], ondelete="CASCADE"),
        )
    _criar_indices(
        bind,
        LOG,
        [
            ("ix_meta_ads_sync_log_mslMacId", ["mslMacId"]),
            ("ix_meta_ads_sync_log_mslDataExecucao", ["mslDataExecucao"]),
        ],
    )

    colunas = {c["name"] for c in inspect(bind).get_columns("oportunidade")}
    if "opoMcgId" not in colunas:
        op.add_column("oportunidade", sa.Column("opoMcgId", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_oportunidade_opoMcgId",
            "oportunidade",
            CAMPANHA,
            ["opoMcgId"],
            ["mcgId"],
            ondelete="SET NULL",
        )
    _criar_indices(bind, "oportunidade", [("ix_oportunidade_opoMcgId", ["opoMcgId"])])
    if "opoMcgManual" not in colunas:
        op.add_column(
            "oportunidade",
            sa.Column("opoMcgManual", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    colunas = {c["name"] for c in inspect(bind).get_columns("oportunidade")}
    if "opoMcgManual" in colunas:
        op.drop_column("oportunidade", "opoMcgManual")
    if "opoMcgId" in colunas:
        op.drop_constraint("fk_oportunidade_opoMcgId", "oportunidade", type_="foreignkey")
        if "ix_oportunidade_opoMcgId" in _indices(bind, "oportunidade"):
            op.drop_index("ix_oportunidade_opoMcgId", table_name="oportunidade")
        op.drop_column("oportunidade", "opoMcgId")
    for tabela in (LOG, INSIGHT, CAMPANHA, ORIGEM, CONTA):
        if tabela in _tabelas(bind):
            op.drop_table(tabela)
```

- [ ] **Step 6: Validar a migration sem banco real**

Run: `.venv/Scripts/python -c "import importlib.util as u; s=u.spec_from_file_location('m','backend/alembic/versions/0030_meta_ads.py'); m=u.module_from_spec(s); s.loader.exec_module(m); print(m.revision, m.down_revision)"`
Expected: `0030_meta_ads 0029_crm_meta_valor_projeto`.

Depois **perguntar ao Carlos** se pode rodar `.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head` contra o banco do `.env`. Não rodar sem o ok.

- [ ] **Step 7: Rodar a suíte inteira**

Run: `.venv/Scripts/python -m unittest $(ls backend/tests/test_*.py | sed 's#/#.#g; s#\.py$##' | tr '\n' ' ')`
Expected: todos OK (eram 199 antes desta task, mais os desta e da Task 1).

- [ ] **Step 8: Commit**

```bash
git add backend/models backend/alembic/versions/0030_meta_ads.py backend/schemas/oportunidade.py backend/tests/banco_sqlite.py backend/tests/test_meta_ads_modelos.py
git commit -m "Meta Ads: tabelas, migration 0030 e banco SQLite para testes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Cliente da Graph API

**Files:**
- Create: `backend/services/meta_ads/__init__.py` (vazio, só docstring), `backend/services/meta_ads/cliente_graph.py`
- Test: `backend/tests/test_meta_ads_cliente_graph.py`

**Interfaces:**
- Consumes: `settings.META_API_VERSION` (Task 1).
- Produces (em `backend.services.meta_ads.cliente_graph`):
  - `normalizar_conta(valor: str) -> str` (levanta `ValueError` em vazio)
  - `extrair_leads(actions: list | None) -> int`
  - exceções `MetaGraphErro(mensagem: str, codigo: int | None)`, `TokenInvalidoErro(MetaGraphErro)`, `ErroTemporario(MetaGraphErro)`; todas expõem `.mensagem` e `.codigo`
  - dataclasses `ContaMeta(nome: str, moeda: str | None, fuso: str | None)`, `CampanhaMeta(id: str, nome: str, objetivo: str | None, status: str | None)`, `InsightDia(campanha_id: str, campanha_nome: str, dia: date, investimento: Decimal, impressoes: int, cliques: int, alcance: int, leads: int)`
  - `class ClienteGraph(token: str, *, versao: str | None = None, transporte: httpx.BaseTransport | None = None, dormir=time.sleep, esperas=(30, 60, 120))`, context manager, com `obter_conta(act_id) -> ContaMeta`, `listar_campanhas(act_id) -> list[CampanhaMeta]`, `listar_insights(act_id, inicio: date, fim: date) -> list[InsightDia]`.

- [ ] **Step 1: Write the failing test** — `backend/tests/test_meta_ads_cliente_graph.py`

```python
import json
import unittest
from datetime import date
from decimal import Decimal

import httpx

from backend.services.meta_ads import cliente_graph as g

TOKEN = "EAAB-token-super-secreto-9999"


def _cliente(respostas, dormidas=None):
    """`respostas`: lista de (status, corpo_dict) devolvidas em ordem; grava as requisicoes."""
    feitas = []
    fila = list(respostas)

    def handler(request: httpx.Request) -> httpx.Response:
        feitas.append(request)
        status, corpo = fila.pop(0)
        return httpx.Response(status, json=corpo)

    dormidas = dormidas if dormidas is not None else []
    cliente = g.ClienteGraph(
        TOKEN, versao="v99.0", transporte=httpx.MockTransport(handler), dormir=dormidas.append
    )
    return cliente, feitas, dormidas


def _erro(codigo, mensagem="falhou"):
    return {"error": {"message": mensagem, "type": "OAuthException", "code": codigo}}


class NormalizacaoTests(unittest.TestCase):
    def test_variacoes_de_conta(self) -> None:
        for entrada in ("act_123", "123", " act_123 ", "act-123"):
            self.assertEqual(g.normalizar_conta(entrada), "act_123", entrada)

    def test_conta_vazia_recusada(self) -> None:
        for entrada in ("", "act_", None):
            with self.assertRaises(ValueError):
                g.normalizar_conta(entrada)


class ExtrairLeadsTests(unittest.TestCase):
    def test_sem_acoes(self) -> None:
        self.assertEqual(g.extrair_leads(None), 0)
        self.assertEqual(g.extrair_leads([]), 0)

    def test_prioridade_conta_so_o_primeiro_tipo(self) -> None:
        acoes = [
            {"action_type": "offsite_conversion.fb_pixel_lead", "value": "9"},
            {"action_type": "lead", "value": "4"},
            {"action_type": "onsite_conversion.lead_grouped", "value": "4"},
        ]
        self.assertEqual(g.extrair_leads(acoes), 4)

    def test_cai_para_o_proximo_tipo(self) -> None:
        acoes = [{"action_type": "offsite_conversion.fb_pixel_lead", "value": "3"}]
        self.assertEqual(g.extrair_leads(acoes), 3)

    def test_ignora_outras_acoes(self) -> None:
        self.assertEqual(g.extrair_leads([{"action_type": "link_click", "value": "50"}]), 0)


class ClienteTests(unittest.TestCase):
    def test_token_vai_no_cabecalho_e_nunca_na_url(self) -> None:
        cliente, feitas, _ = _cliente(
            [(200, {"name": "Conta X", "currency": "BRL", "timezone_name": "America/Sao_Paulo"})]
        )
        with cliente:
            info = cliente.obter_conta("act_1")
        self.assertEqual(info, g.ContaMeta(nome="Conta X", moeda="BRL", fuso="America/Sao_Paulo"))
        self.assertEqual(feitas[0].headers["Authorization"], f"Bearer {TOKEN}")
        self.assertNotIn(TOKEN, str(feitas[0].url))
        self.assertIn("/v99.0/act_1", str(feitas[0].url))

    def test_campanhas_seguem_paginacao(self) -> None:
        pagina1 = {
            "data": [{"id": "1", "name": "A", "objective": "OUTCOME_LEADS", "effective_status": "ACTIVE"}],
            "paging": {"next": "https://graph.facebook.com/v99.0/act_1/campaigns?after=x"},
        }
        pagina2 = {"data": [{"id": "2", "name": "B"}], "paging": {}}
        cliente, feitas, _ = _cliente([(200, pagina1), (200, pagina2)])
        with cliente:
            campanhas = cliente.listar_campanhas("act_1")
        self.assertEqual([c.id for c in campanhas], ["1", "2"])
        self.assertEqual(campanhas[1].objetivo, None)
        self.assertEqual(len(feitas), 2)
        self.assertNotIn(TOKEN, str(feitas[1].url))

    def test_insights_convertem_tipos(self) -> None:
        corpo = {
            "data": [
                {
                    "campaign_id": "10",
                    "campaign_name": "Leads Outubro",
                    "date_start": "2026-10-01",
                    "date_stop": "2026-10-01",
                    "spend": "123.45",
                    "impressions": "1000",
                    "clicks": "37",
                    "reach": "800",
                    "actions": [{"action_type": "lead", "value": "5"}],
                }
            ]
        }
        cliente, feitas, _ = _cliente([(200, corpo)])
        with cliente:
            linhas = cliente.listar_insights("act_1", date(2026, 10, 1), date(2026, 10, 2))
        self.assertEqual(
            linhas,
            [
                g.InsightDia(
                    campanha_id="10",
                    campanha_nome="Leads Outubro",
                    dia=date(2026, 10, 1),
                    investimento=Decimal("123.45"),
                    impressoes=1000,
                    cliques=37,
                    alcance=800,
                    leads=5,
                )
            ],
        )
        params = feitas[0].url.params
        self.assertEqual(params["level"], "campaign")
        self.assertEqual(params["time_increment"], "1")
        self.assertEqual(
            json.loads(params["time_range"]), {"since": "2026-10-01", "until": "2026-10-02"}
        )

    def test_token_invalido_nao_retenta(self) -> None:
        cliente, feitas, dormidas = _cliente([(400, _erro(190, "Error validating access token"))])
        with cliente, self.assertRaises(g.TokenInvalidoErro) as ctx:
            cliente.obter_conta("act_1")
        self.assertEqual(len(feitas), 1)
        self.assertEqual(dormidas, [])
        self.assertEqual(ctx.exception.codigo, 190)

    def test_limite_retenta_com_espera_crescente(self) -> None:
        cliente, feitas, dormidas = _cliente(
            [(400, _erro(17)), (400, _erro(17)), (200, {"name": "ok"})]
        )
        with cliente:
            cliente.obter_conta("act_1")
        self.assertEqual(dormidas, [30, 60])
        self.assertEqual(len(feitas), 3)

    def test_limite_esgotado_vira_erro_temporario(self) -> None:
        cliente, feitas, dormidas = _cliente([(400, _erro(4))] * 4)
        with cliente, self.assertRaises(g.ErroTemporario):
            cliente.obter_conta("act_1")
        self.assertEqual(dormidas, [30, 60, 120])
        self.assertEqual(len(feitas), 4)

    def test_5xx_e_temporario(self) -> None:
        cliente, _, dormidas = _cliente([(503, {}), (200, {"name": "ok"})])
        with cliente:
            cliente.obter_conta("act_1")
        self.assertEqual(dormidas, [30])

    def test_erro_comum_nao_retenta(self) -> None:
        cliente, feitas, _ = _cliente([(400, _erro(100, "Invalid parameter"))])
        with cliente, self.assertRaises(g.MetaGraphErro) as ctx:
            cliente.obter_conta("act_1")
        self.assertNotIsInstance(ctx.exception, (g.TokenInvalidoErro, g.ErroTemporario))
        self.assertIn("Invalid parameter", ctx.exception.mensagem)
        self.assertEqual(len(feitas), 1)

    def test_mensagem_nunca_contem_o_token(self) -> None:
        cliente, _, _ = _cliente([(400, _erro(100, f"token {TOKEN} ruim"))])
        with cliente, self.assertRaises(g.MetaGraphErro) as ctx:
            cliente.obter_conta("act_1")
        self.assertNotIn(TOKEN, ctx.exception.mensagem)
        self.assertNotIn(TOKEN, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_cliente_graph -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'backend.services.meta_ads'`.

- [ ] **Step 3: Implementar**

`backend/services/meta_ads/__init__.py`:

```python
"""Integracao com o Meta Ads: campanhas, custo e retorno por empresa."""
```

`backend/services/meta_ads/cliente_graph.py`:

```python
"""
Cliente minimo da Graph API do Meta, somente leitura (conta, campanhas e insights).

O token vai sempre no cabecalho Authorization, nunca na URL: assim ele nao vaza em log de
proxy, em paging.next nem em mensagem de erro. Erros do Meta viram tres excecoes:
TokenInvalidoErro (parar e pedir token novo), ErroTemporario (limite de chamadas, 5xx ou
rede: retentado com espera crescente) e MetaGraphErro (o resto).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import httpx

from ...config import settings

BASE_URL = "https://graph.facebook.com"
# 190: token invalido/expirado; 102: sessao; 200/10: sem permissao na conta.
CODIGOS_TOKEN = frozenset({190, 102, 200, 10})
CODIGOS_LIMITE = frozenset({4, 17, 32, 613, 80004})
# O Meta reporta o mesmo lead em mais de um tipo; conta-se so o primeiro presente.
TIPOS_LEAD = ("lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead")
ESPERAS_PADRAO = (30, 60, 120)


class MetaGraphErro(Exception):
    def __init__(self, mensagem: str, codigo: int | None = None) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo


class TokenInvalidoErro(MetaGraphErro):
    pass


class ErroTemporario(MetaGraphErro):
    pass


@dataclass(frozen=True)
class ContaMeta:
    nome: str
    moeda: str | None
    fuso: str | None


@dataclass(frozen=True)
class CampanhaMeta:
    id: str
    nome: str
    objetivo: str | None
    status: str | None


@dataclass(frozen=True)
class InsightDia:
    campanha_id: str
    campanha_nome: str
    dia: date
    investimento: Decimal
    impressoes: int
    cliques: int
    alcance: int
    leads: int


def normalizar_conta(valor: str | None) -> str:
    digitos = re.sub(r"\D", "", valor or "")
    if not digitos:
        raise ValueError("Informe o id da conta de anúncios (ex.: act_1234567890)")
    return "act_" + digitos


def _inteiro(valor) -> int:
    if valor in (None, ""):
        return 0
    return int(float(valor))


def extrair_leads(actions: list | None) -> int:
    por_tipo = {a.get("action_type"): a.get("value") for a in actions or []}
    for tipo in TIPOS_LEAD:
        if tipo in por_tipo:
            return _inteiro(por_tipo[tipo])
    return 0


class ClienteGraph:
    def __init__(
        self,
        token: str,
        *,
        versao: str | None = None,
        transporte: httpx.BaseTransport | None = None,
        dormir: Callable[[float], None] = time.sleep,
        esperas: tuple[float, ...] = ESPERAS_PADRAO,
    ) -> None:
        self._token = token
        self._dormir = dormir
        self._esperas = esperas
        self._http = httpx.Client(
            base_url=f"{BASE_URL}/{versao or settings.META_API_VERSION}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60.0,
            transport=transporte,
        )

    def __enter__(self) -> "ClienteGraph":
        return self

    def __exit__(self, *_exc) -> None:
        self._http.close()

    def obter_conta(self, act_id: str) -> ContaMeta:
        dados = self._get(f"/{act_id}", {"fields": "name,currency,timezone_name,account_status"})
        return ContaMeta(
            nome=dados.get("name") or act_id,
            moeda=dados.get("currency"),
            fuso=dados.get("timezone_name"),
        )

    def listar_campanhas(self, act_id: str) -> list[CampanhaMeta]:
        params = {"fields": "id,name,objective,effective_status", "limit": 500}
        return [
            CampanhaMeta(
                id=str(c["id"]),
                nome=c.get("name") or str(c["id"]),
                objetivo=c.get("objective"),
                status=c.get("effective_status"),
            )
            for c in self._paginar(f"/{act_id}/campaigns", params)
        ]

    def listar_insights(self, act_id: str, inicio: date, fim: date) -> list[InsightDia]:
        params = {
            "level": "campaign",
            "time_increment": 1,
            "time_range": json.dumps({"since": inicio.isoformat(), "until": fim.isoformat()}),
            "fields": "campaign_id,campaign_name,spend,impressions,clicks,reach,actions",
            "limit": 500,
        }
        return [
            InsightDia(
                campanha_id=str(linha["campaign_id"]),
                campanha_nome=linha.get("campaign_name") or str(linha["campaign_id"]),
                dia=date.fromisoformat(linha["date_start"]),
                investimento=Decimal(str(linha.get("spend") or "0")),
                impressoes=_inteiro(linha.get("impressions")),
                cliques=_inteiro(linha.get("clicks")),
                alcance=_inteiro(linha.get("reach")),
                leads=extrair_leads(linha.get("actions")),
            )
            for linha in self._paginar(f"/{act_id}/insights", params)
        ]

    def _paginar(self, caminho: str, params: dict) -> Iterator[dict]:
        dados = self._get(caminho, params)
        while True:
            yield from dados.get("data", [])
            proxima = (dados.get("paging") or {}).get("next")
            if not proxima:
                return
            dados = self._get(proxima, None)

    def _get(self, url: str, params: dict | None) -> dict:
        tentativa = 0
        while True:
            try:
                resposta = self._http.get(url, params=params)
            except httpx.TransportError as exc:
                erro: MetaGraphErro = ErroTemporario(
                    f"Falha de rede ao falar com o Meta ({type(exc).__name__})."
                )
            else:
                if resposta.status_code == 200:
                    return resposta.json()
                erro = self._traduzir(resposta)
            if not isinstance(erro, ErroTemporario) or tentativa >= len(self._esperas):
                raise erro
            self._dormir(self._esperas[tentativa])
            tentativa += 1

    def _traduzir(self, resposta: httpx.Response) -> MetaGraphErro:
        try:
            corpo = resposta.json().get("error") or {}
        except ValueError:
            corpo = {}
        codigo = corpo.get("code")
        detalhe = str(corpo.get("message") or f"HTTP {resposta.status_code}")
        detalhe = detalhe.replace(self._token, "***")[:300]
        if codigo in CODIGOS_TOKEN:
            return TokenInvalidoErro(
                "Token inválido, expirado ou sem acesso à conta — gere um novo no "
                f"Business Manager. ({detalhe})",
                codigo,
            )
        if codigo in CODIGOS_LIMITE or resposta.status_code >= 500:
            return ErroTemporario(
                f"Meta indisponível ou limite de chamadas atingido. ({detalhe})", codigo
            )
        return MetaGraphErro(f"Erro do Meta: {detalhe}", codigo)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_cliente_graph -v`
Expected: 15 testes OK.

- [ ] **Step 5: Commit**

```bash
git add backend/services/meta_ads/__init__.py backend/services/meta_ads/cliente_graph.py backend/tests/test_meta_ads_cliente_graph.py
git commit -m "Meta Ads: cliente da Graph API com retentativa e token no cabeçalho

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Vínculo lead → campanha

**Files:**
- Create: `backend/services/meta_ads/vinculo.py`
- Modify: `backend/services/lead_intake_service.py` (antes de `db.commit()` em `_criar` e em `_atualizar`)
- Test: `backend/tests/test_meta_ads_vinculo.py`

**Interfaces:**
- Consumes: models da Task 2; fábricas de `banco_sqlite`.
- Produces (em `backend.services.meta_ads.vinculo`): `CAMPOS_CANDIDATOS: tuple[str, ...]`, `normalizar_nome(texto: str | None) -> str`, `candidatos(opo) -> set[str]`, `class IndiceCampanhas` com `IndiceCampanhas.da_empresa(db, emp_id) -> IndiceCampanhas` e `.resolver(textos: set[str]) -> int | None`, `vincular_oportunidade(db, opo, indice: IndiceCampanhas | None = None) -> bool` (não faz commit), `vincular_pendentes(db, emp_id) -> int` (não faz commit).

- [ ] **Step 1: Write the failing test** — `backend/tests/test_meta_ads_vinculo.py`

```python
import unittest

from backend.services.meta_ads import vinculo
from backend.tests import banco_sqlite as b

NOME = "CP030326 | LEADS | ABO | FRONTEND OFFER | PLAYBOOK | AD TESTING"


class NormalizacaoTests(unittest.TestCase):
    def test_minusculas_e_espacos(self) -> None:
        self.assertEqual(vinculo.normalizar_nome("  CP03  |  Leads \n"), "cp03 | leads")

    def test_vazio(self) -> None:
        self.assertEqual(vinculo.normalizar_nome(None), "")
        self.assertEqual(vinculo.normalizar_nome("   "), "")


class VinculoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.conta = b.criar_conta(self.db, self.emp.empId, act="act_1")
        self.camp = b.criar_campanha(self.db, self.conta, "120210000001", NOME)

    def test_liga_pelo_nome_em_utm_source(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME.lower() + "  ")
        self.assertTrue(vinculo.vincular_oportunidade(self.db, opo))
        self.assertEqual(opo.opoMcgId, self.camp.mcgId)

    def test_liga_pelo_id_da_campanha(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoUtmCampaign="120210000001")
        self.assertTrue(vinculo.vincular_oportunidade(self.db, opo))

    def test_sem_candidato_nao_liga(self) -> None:
        opo = b.criar_oportunidade(self.db, self.emp.empId)
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))
        self.assertIsNone(opo.opoMcgId)

    def test_nome_ambiguo_nao_liga(self) -> None:
        outra = b.criar_conta(self.db, self.emp.empId, act="act_2")
        b.criar_campanha(self.db, outra, "999", NOME)
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME)
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))
        self.assertIsNone(opo.opoMcgId)

    def test_campanha_de_outra_empresa_nao_liga(self) -> None:
        outra_emp = b.criar_empresa(self.db, "Outra")
        opo = b.criar_oportunidade(self.db, outra_emp.empId, opoUtmSource=NOME)
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))

    def test_manual_e_preservado(self) -> None:
        opo = b.criar_oportunidade(
            self.db, self.emp.empId, opoUtmSource=NOME, opoMcgId=None, opoMcgManual=True
        )
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))
        self.assertIsNone(opo.opoMcgId)

    def test_ja_ligada_nao_muda(self) -> None:
        outra = b.criar_campanha(self.db, self.conta, "555", "Outra campanha")
        opo = b.criar_oportunidade(
            self.db, self.emp.empId, opoUtmSource=NOME, opoMcgId=outra.mcgId
        )
        self.assertFalse(vinculo.vincular_oportunidade(self.db, opo))
        self.assertEqual(opo.opoMcgId, outra.mcgId)

    def test_vincular_pendentes_conta_e_respeita_regras(self) -> None:
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME)
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmTerm="120210000001")
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource=NOME, opoMcgManual=True)
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource="outra coisa")
        self.assertEqual(vinculo.vincular_pendentes(self.db, self.emp.empId), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_vinculo -v`
Expected: FAIL com `ImportError: cannot import name 'vinculo'`.

- [ ] **Step 3: Implementar** — `backend/services/meta_ads/vinculo.py`

```python
"""
Liga oportunidades as campanhas do Meta pelo texto que chega nos campos UTM.

Regra: normaliza (minusculas, espacos colapsados) cada campo candidato e procura, na
empresa do lead, campanha com aquele id externo ou aquele nome normalizado. Liga so se
exatamente UMA campanha casar. Nunca mexe em oportunidade ja ligada ou marcada como manual.
Nenhuma funcao daqui faz commit: quem chama decide a transacao.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ...models.meta_ads_campanha import MetaAdsCampanha
from ...models.oportunidade import Oportunidade

CAMPOS_CANDIDATOS = (
    "opoUtmCampaign",
    "opoUtmSource",
    "opoUtmContent",
    "opoUtmTerm",
    "opoOrigemExternalId",
)


def normalizar_nome(texto: str | None) -> str:
    return " ".join((texto or "").split()).lower()


def candidatos(opo) -> set[str]:
    textos = (normalizar_nome(getattr(opo, campo, None)) for campo in CAMPOS_CANDIDATOS)
    return {t for t in textos if t}


class IndiceCampanhas:
    """Campanhas de uma empresa indexadas por id externo e por nome normalizado."""

    def __init__(self, linhas) -> None:
        self._por_texto: dict[str, set[int]] = {}
        for mcg_id, externa, nome_normalizado in linhas:
            for chave in (externa, nome_normalizado):
                if chave:
                    self._por_texto.setdefault(chave, set()).add(mcg_id)

    @classmethod
    def da_empresa(cls, db: Session, emp_id: int) -> "IndiceCampanhas":
        linhas = db.execute(
            select(
                MetaAdsCampanha.mcgId,
                MetaAdsCampanha.mcgCampanhaExterna,
                MetaAdsCampanha.mcgNomeNormalizado,
            ).where(MetaAdsCampanha.mcgEmpId == emp_id)
        ).all()
        return cls(linhas)

    def resolver(self, textos: set[str]) -> int | None:
        achados: set[int] = set()
        for texto in textos:
            achados |= self._por_texto.get(texto, set())
        return next(iter(achados)) if len(achados) == 1 else None


def vincular_oportunidade(
    db: Session, opo: Oportunidade, indice: IndiceCampanhas | None = None
) -> bool:
    if opo.opoMcgManual or opo.opoMcgId is not None:
        return False
    textos = candidatos(opo)
    if not textos:
        return False
    indice = indice or IndiceCampanhas.da_empresa(db, opo.opoEmpId)
    mcg_id = indice.resolver(textos)
    if mcg_id is None:
        return False
    opo.opoMcgId = mcg_id
    return True


def vincular_pendentes(db: Session, emp_id: int) -> int:
    indice = IndiceCampanhas.da_empresa(db, emp_id)
    tem_candidato = or_(*[getattr(Oportunidade, c).isnot(None) for c in CAMPOS_CANDIDATOS])
    pendentes = db.execute(
        select(Oportunidade).where(
            Oportunidade.opoEmpId == emp_id,
            Oportunidade.opoMcgId.is_(None),
            Oportunidade.opoMcgManual.is_(False),
            tem_candidato,
        )
    ).scalars()
    return sum(1 for opo in pendentes if vincular_oportunidade(db, opo, indice))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_vinculo -v`
Expected: 10 testes OK.

- [ ] **Step 5: Ligar na entrada de leads**

Em `backend/services/lead_intake_service.py`, adicionar ao bloco de imports de serviços:

```python
from .meta_ads import vinculo as vinculo_meta_ads
```

e, junto das funções auxiliares (depois de `_historico`):

```python
def _vincular_campanha_meta(db: Session, oportunidade: Oportunidade) -> None:
    # Best-effort: o lead nunca deixa de entrar por causa do vinculo com o Meta Ads.
    try:
        vinculo_meta_ads.vincular_oportunidade(db, oportunidade)
    except Exception:
        logger.exception(
            "Falha ao vincular campanha Meta na oportunidade %s", oportunidade.opoId
        )
```

Em `_criar`, imediatamente antes de `webhook_emitter.enfileirar(` (o bloco comentado "Antes do commit…"), inserir:

```python
    _vincular_campanha_meta(db, oportunidade)
```

Em `_atualizar`, imediatamente antes de `webhook_emitter.enfileirar(` (o `lead.updated`), inserir a mesma linha.

- [ ] **Step 6: Rodar os testes de entrada de leads**

Run: `.venv/Scripts/python -m unittest backend.tests.test_lead_dedup backend.tests.test_lead_normalizacao backend.tests.test_meta_ads_vinculo -v`
Expected: todos OK.

- [ ] **Step 7: Commit**

```bash
git add backend/services/meta_ads/vinculo.py backend/services/lead_intake_service.py backend/tests/test_meta_ads_vinculo.py
git commit -m "Meta Ads: vínculo automático de lead com campanha pelo nome ou id

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Sincronização de uma conta

**Files:**
- Create: `backend/services/meta_ads/sincronizacao.py`
- Test: `backend/tests/test_meta_ads_sincronizacao.py`

**Interfaces:**
- Consumes: `cliente_graph` (Task 3: `ClienteGraph`, `TokenInvalidoErro`, `ErroTemporario`, `MetaGraphErro`, `CampanhaMeta`, `InsightDia`), `vinculo.normalizar_nome`, `vinculo.vincular_pendentes` (Task 4), `cripto.decifrar` (Task 1), models e constantes de status (Task 2).
- Produces (em `backend.services.meta_ads.sincronizacao`): constantes `JANELA_DIAS=30`, `CARGA_INICIAL_DIAS=90`, `MAX_DIAS_PERIODO=366`, `TRAVA_MINUTOS=30`; `@dataclass ResultadoSync(status: str, linhas: int = 0, leads_vinculados: int = 0, erro: str | None = None)`; `hoje_da_conta(conta, agora_utc: datetime | None = None) -> date`; `janela_padrao(conta, hoje: date) -> tuple[date, date]`; `reivindicar(db, mac_id: int) -> bool` (faz commit); `sincronizar_conta(db, mac_id: int, *, origem: str, inicio: date | None = None, fim: date | None = None, fabrica_cliente=ClienteGraph) -> ResultadoSync` (exige trava já pega; sempre libera a trava e grava log); `executar_em_sessao_propria(mac_id: int, origem: str, inicio: date | None = None, fim: date | None = None) -> ResultadoSync`; `contas_da_rodada_diaria(db) -> list[int]`; `sincronizar_todas_agendadas() -> int`.

- [ ] **Step 1: Write the failing test** — `backend/tests/test_meta_ads_sincronizacao.py`

```python
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from backend.core.tempo import utcnow
from backend.models.meta_ads_campanha import MetaAdsCampanha
from backend.models.meta_ads_conta import (
    STATUS_AVISO,
    STATUS_ERRO,
    STATUS_OK,
    STATUS_SINCRONIZANDO,
    STATUS_TOKEN_INVALIDO,
)
from backend.models.meta_ads_insight_diario import MetaAdsInsightDiario
from backend.models.meta_ads_sync_log import MetaAdsSyncLog
from backend.services.meta_ads import cliente_graph as g
from backend.services.meta_ads import sincronizacao as s
from backend.tests import banco_sqlite as b


def _insight(cid, nome, dia, inv, leads=0):
    return g.InsightDia(cid, nome, dia, Decimal(str(inv)), 1000, 40, 800, leads)


class ClienteFalso:
    """Substitui ClienteGraph. Guarda o token e os periodos pedidos."""

    def __init__(self, campanhas=(), insights=(), erro=None):
        self.campanhas = list(campanhas)
        self.insights = list(insights)
        self.erro = erro
        self.token = None
        self.periodos = []

    def __call__(self, token):
        self.token = token
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def listar_campanhas(self, _act):
        return self.campanhas

    def listar_insights(self, _act, inicio, fim):
        self.periodos.append((inicio, fim))
        if self.erro:
            raise self.erro
        return self.insights


class SincronizacaoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.conta = b.criar_conta(self.db, self.emp.empId, token="EAAB-token-correto-1234")

    def _sync(self, cliente, **kw):
        self.assertTrue(s.reivindicar(self.db, self.conta.macId))
        return s.sincronizar_conta(
            self.db, self.conta.macId, origem=kw.pop("origem", "manual"), fabrica_cliente=cliente, **kw
        )

    def _insights(self):
        return self.db.execute(
            select(MetaAdsInsightDiario).order_by(MetaAdsInsightDiario.midData)
        ).scalars().all()

    def test_grava_campanhas_e_insights(self) -> None:
        cliente = ClienteFalso(
            campanhas=[g.CampanhaMeta("1", "Leads Out", "OUTCOME_LEADS", "ACTIVE")],
            insights=[_insight("1", "Leads Out", date(2026, 10, 1), "10.50", leads=2)],
        )
        r = self._sync(cliente, inicio=date(2026, 10, 1), fim=date(2026, 10, 2))
        self.assertEqual((r.status, r.linhas), (STATUS_OK, 1))
        self.assertEqual(cliente.token, "EAAB-token-correto-1234")
        camp = self.db.execute(select(MetaAdsCampanha)).scalar_one()
        self.assertEqual((camp.mcgNome, camp.mcgNomeNormalizado, camp.mcgStatus), ("Leads Out", "leads out", "ACTIVE"))
        linha = self._insights()[0]
        self.assertEqual((float(linha.midInvestimento), linha.midLeadsMeta, linha.midMcgId), (10.5, 2, camp.mcgId))
        self.db.refresh(self.conta)
        self.assertEqual(self.conta.macStatus, STATUS_OK)
        self.assertIsNone(self.conta.macSyncIniciadaEm)
        self.assertIsNotNone(self.conta.macUltimaSync)

    def test_regrava_periodo_sem_sobras_e_preserva_fora_dele(self) -> None:
        camp = [g.CampanhaMeta("1", "A", None, "ACTIVE")]
        self._sync(
            ClienteFalso(camp, [_insight("1", "A", date(2026, 9, 30), 5), _insight("1", "A", date(2026, 10, 1), 7)]),
            inicio=date(2026, 9, 30),
            fim=date(2026, 10, 1),
        )
        self._sync(ClienteFalso(camp, []), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual([l.midData for l in self._insights()], [date(2026, 9, 30)])

    def test_campanha_so_nos_insights_e_criada(self) -> None:
        self._sync(
            ClienteFalso([], [_insight("77", "Excluída", date(2026, 10, 1), 3)]),
            inicio=date(2026, 10, 1),
            fim=date(2026, 10, 1),
        )
        camp = self.db.execute(select(MetaAdsCampanha)).scalar_one()
        self.assertEqual((camp.mcgCampanhaExterna, camp.mcgNome), ("77", "Excluída"))

    def test_renomear_campanha_mantem_vinculo(self) -> None:
        self._sync(ClienteFalso([g.CampanhaMeta("1", "Nome antigo", None, "ACTIVE")]), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        camp = self.db.execute(select(MetaAdsCampanha)).scalar_one()
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoMcgId=camp.mcgId)
        self._sync(ClienteFalso([g.CampanhaMeta("1", "Nome novo", None, "PAUSED")]), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.db.refresh(camp)
        self.db.refresh(opo)
        self.assertEqual((camp.mcgNome, camp.mcgStatus), ("Nome novo", "PAUSED"))
        self.assertEqual(opo.opoMcgId, camp.mcgId)

    def test_erro_no_meio_nao_grava_nada_e_registra(self) -> None:
        camp = [g.CampanhaMeta("1", "A", None, "ACTIVE")]
        self._sync(ClienteFalso(camp, [_insight("1", "A", date(2026, 10, 1), 5)]), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        r = self._sync(
            ClienteFalso([g.CampanhaMeta("1", "Renomeada", None, "ACTIVE")], erro=g.MetaGraphErro("Erro do Meta: x", 100)),
            inicio=date(2026, 10, 1),
            fim=date(2026, 10, 1),
        )
        self.assertEqual(r.status, STATUS_ERRO)
        self.assertEqual(len(self._insights()), 1)
        self.assertEqual(self.db.execute(select(MetaAdsCampanha)).scalar_one().mcgNome, "A")
        self.db.refresh(self.conta)
        self.assertEqual((self.conta.macStatus, self.conta.macMensagem), (STATUS_ERRO, "Erro do Meta: x"))
        log = self.db.execute(select(MetaAdsSyncLog).order_by(MetaAdsSyncLog.mslId.desc())).scalars().first()
        self.assertEqual((log.mslStatus, log.mslErro, log.mslOrigem), (STATUS_ERRO, "Erro do Meta: x", "manual"))

    def test_token_invalido_marca_status_proprio(self) -> None:
        r = self._sync(ClienteFalso(erro=g.TokenInvalidoErro("Token inválido", 190)), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual(r.status, STATUS_TOKEN_INVALIDO)
        self.assertEqual(s.contas_da_rodada_diaria(self.db), [])

    def test_erro_temporario_vira_aviso(self) -> None:
        r = self._sync(ClienteFalso(erro=g.ErroTemporario("limite", 17)), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual(r.status, STATUS_AVISO)
        self.assertEqual(s.contas_da_rodada_diaria(self.db), [self.conta.macId])

    def test_token_ilegivel_vira_token_invalido(self) -> None:
        self.conta.macToken = "enc:v1:lixo"
        self.db.commit()
        r = self._sync(ClienteFalso(), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual(r.status, STATUS_TOKEN_INVALIDO)

    def test_carga_inicial_de_90_dias_e_depois_30(self) -> None:
        cliente = ClienteFalso()
        self._sync(cliente, origem="agendada")
        inicio, fim = cliente.periodos[0]
        self.assertEqual((fim - inicio).days, 90)
        log = self.db.execute(select(MetaAdsSyncLog)).scalar_one()
        self.assertEqual(log.mslOrigem, "carga_inicial")
        self._sync(cliente, origem="agendada")
        inicio, fim = cliente.periodos[1]
        self.assertEqual((fim - inicio).days, 30)

    def test_periodo_explicito_nao_marca_carga_inicial(self) -> None:
        self._sync(ClienteFalso(), origem="periodo", inicio=date(2026, 10, 1), fim=date(2026, 10, 2))
        self.db.refresh(self.conta)
        self.assertFalse(self.conta.macCargaInicialFeita)

    def test_vincula_leads_depois_de_sincronizar(self) -> None:
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource="leads out")
        r = self._sync(ClienteFalso([g.CampanhaMeta("1", "Leads Out", None, "ACTIVE")]), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual(r.leads_vinculados, 1)


class TravaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.conta = b.criar_conta(self.db, self.emp.empId)

    def test_segunda_reivindicacao_falha(self) -> None:
        self.assertTrue(s.reivindicar(self.db, self.conta.macId))
        self.assertFalse(s.reivindicar(self.db, self.conta.macId))

    def test_trava_velha_e_liberada(self) -> None:
        self.conta.macStatus = STATUS_SINCRONIZANDO
        self.conta.macSyncIniciadaEm = utcnow() - timedelta(minutes=31)
        self.db.commit()
        self.assertTrue(s.reivindicar(self.db, self.conta.macId))

    def test_conta_inativa_nao_e_reivindicada(self) -> None:
        self.conta.macAtivo = False
        self.db.commit()
        self.assertFalse(s.reivindicar(self.db, self.conta.macId))


class DatasTests(unittest.TestCase):
    def test_hoje_no_fuso_da_conta(self) -> None:
        class Conta:
            macFuso = "America/Los_Angeles"

        # 02:00 UTC de 15/10 ainda e 14/10 em Los Angeles.
        self.assertEqual(s.hoje_da_conta(Conta(), datetime(2026, 10, 15, 2, 0)), date(2026, 10, 14))

    def test_fuso_invalido_cai_no_padrao(self) -> None:
        class Conta:
            macFuso = "Fuso/Inexistente"

        self.assertEqual(s.hoje_da_conta(Conta(), datetime(2026, 10, 15, 12, 0)), date(2026, 10, 15))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_sincronizacao -v`
Expected: FAIL com `ImportError: cannot import name 'sincronizacao'`.

- [ ] **Step 3: Implementar** — `backend/services/meta_ads/sincronizacao.py`

```python
"""
Sincronizacao de uma conta de anuncios: campanhas + insights diarios + vinculo dos leads.

Protocolo: quem dispara pega a trava com `reivindicar` (UPDATE condicional, seguro entre
requisicoes concorrentes) e so entao chama `sincronizar_conta`, que SEMPRE libera a trava
e grava uma linha em meta_ads_sync_log. Dados novos e status "ok" entram no mesmo commit;
em qualquer erro ha rollback e nada parcial fica gravado.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from ...core.cripto import decifrar
from ...core.tempo import utcnow
from ...models.meta_ads_campanha import MetaAdsCampanha
from ...models.meta_ads_conta import (
    STATUS_AVISO,
    STATUS_ERRO,
    STATUS_OK,
    STATUS_SINCRONIZANDO,
    STATUS_TOKEN_INVALIDO,
    MetaAdsConta,
)
from ...models.meta_ads_insight_diario import MetaAdsInsightDiario
from ...models.meta_ads_sync_log import MetaAdsSyncLog
from . import vinculo
from .cliente_graph import ClienteGraph, ErroTemporario, MetaGraphErro, TokenInvalidoErro

logger = logging.getLogger(__name__)

JANELA_DIAS = 30
CARGA_INICIAL_DIAS = 90
MAX_DIAS_PERIODO = 366
TRAVA_MINUTOS = 30
FUSO_PADRAO = "America/Sao_Paulo"


@dataclass
class ResultadoSync:
    status: str
    linhas: int = 0
    leads_vinculados: int = 0
    erro: str | None = None


def hoje_da_conta(conta, agora_utc: datetime | None = None) -> date:
    try:
        fuso = ZoneInfo(conta.macFuso or FUSO_PADRAO)
    except (ZoneInfoNotFoundError, ValueError):
        fuso = ZoneInfo(FUSO_PADRAO)
    agora = (agora_utc or utcnow()).replace(tzinfo=timezone.utc)
    return agora.astimezone(fuso).date()


def janela_padrao(conta, hoje: date) -> tuple[date, date]:
    dias = JANELA_DIAS if conta.macCargaInicialFeita else CARGA_INICIAL_DIAS
    return hoje - timedelta(days=dias), hoje


def reivindicar(db: Session, mac_id: int) -> bool:
    agora = utcnow()
    resultado = db.execute(
        update(MetaAdsConta)
        .where(
            MetaAdsConta.macId == mac_id,
            MetaAdsConta.macAtivo.is_(True),
            or_(
                MetaAdsConta.macStatus != STATUS_SINCRONIZANDO,
                MetaAdsConta.macSyncIniciadaEm.is_(None),
                MetaAdsConta.macSyncIniciadaEm < agora - timedelta(minutes=TRAVA_MINUTOS),
            ),
        )
        .values(macStatus=STATUS_SINCRONIZANDO, macSyncIniciadaEm=agora)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return resultado.rowcount == 1


def sincronizar_conta(
    db: Session,
    mac_id: int,
    *,
    origem: str,
    inicio: date | None = None,
    fim: date | None = None,
    fabrica_cliente=ClienteGraph,
) -> ResultadoSync:
    # populate_existing: o UPDATE de `reivindicar` nao sincroniza o identity map; sem isto
    # a conta em memoria pode estar velha e a liberacao da trava nao seria gravada.
    conta = db.get(MetaAdsConta, mac_id, populate_existing=True)
    t0 = time.perf_counter()
    janela_explicita = inicio is not None and fim is not None
    if not janela_explicita:
        inicio, fim = janela_padrao(conta, hoje_da_conta(conta))
        if not conta.macCargaInicialFeita:
            origem = "carga_inicial"
    try:
        token = decifrar(conta.macToken)
        if token is None:
            raise TokenInvalidoErro(
                "Token ilegível (a chave de criptografia mudou) — cadastre o token de novo."
            )
        with fabrica_cliente(token) as cliente:
            campanhas = cliente.listar_campanhas(conta.macContaExterna)
            insights = cliente.listar_insights(conta.macContaExterna, inicio, fim)
        linhas = _gravar(db, conta, campanhas, insights, inicio, fim)
        vinculados = vinculo.vincular_pendentes(db, conta.macEmpId)
        resultado = ResultadoSync(STATUS_OK, linhas, vinculados)
    except TokenInvalidoErro as exc:
        db.rollback()
        resultado = ResultadoSync(STATUS_TOKEN_INVALIDO, erro=exc.mensagem)
    except ErroTemporario as exc:
        db.rollback()
        resultado = ResultadoSync(STATUS_AVISO, erro=exc.mensagem)
    except MetaGraphErro as exc:
        db.rollback()
        resultado = ResultadoSync(STATUS_ERRO, erro=exc.mensagem)
    except Exception as exc:
        db.rollback()
        logger.exception("Falha interna na sincronizacao Meta Ads da conta %s", mac_id)
        resultado = ResultadoSync(
            STATUS_ERRO, erro=f"Falha interna na sincronização ({type(exc).__name__})."
        )
    duracao_ms = int((time.perf_counter() - t0) * 1000)
    _finalizar(db, mac_id, resultado, inicio, fim, origem, duracao_ms, not janela_explicita)
    return resultado


def _gravar(db: Session, conta: MetaAdsConta, campanhas, insights, inicio: date, fim: date) -> int:
    existentes = {
        c.mcgCampanhaExterna: c
        for c in db.execute(
            select(MetaAdsCampanha).where(MetaAdsCampanha.mcgMacId == conta.macId)
        ).scalars()
    }

    def _obter(externa: str, nome: str) -> MetaAdsCampanha:
        camp = existentes.get(externa)
        if camp is None:
            camp = MetaAdsCampanha(
                mcgEmpId=conta.macEmpId, mcgMacId=conta.macId, mcgCampanhaExterna=externa
            )
            db.add(camp)
            existentes[externa] = camp
            camp.mcgNome = nome[:400]
            camp.mcgNomeNormalizado = vinculo.normalizar_nome(nome)[:400]
        return camp

    for c in campanhas:
        camp = _obter(c.id, c.nome)
        camp.mcgNome = c.nome[:400]
        camp.mcgNomeNormalizado = vinculo.normalizar_nome(c.nome)[:400]
        camp.mcgObjetivo = c.objetivo
        camp.mcgStatus = c.status
    for i in insights:
        _obter(i.campanha_id, i.campanha_nome)
    db.flush()

    db.execute(
        delete(MetaAdsInsightDiario).where(
            MetaAdsInsightDiario.midMacId == conta.macId,
            MetaAdsInsightDiario.midData >= inicio,
            MetaAdsInsightDiario.midData <= fim,
        )
    )
    # Defensivo: se o Meta repetir campanha x dia, soma em vez de violar a chave unica.
    por_chave: dict[tuple[int, date], MetaAdsInsightDiario] = {}
    for i in insights:
        mcg_id = existentes[i.campanha_id].mcgId
        linha = por_chave.get((mcg_id, i.dia))
        if linha is None:
            linha = MetaAdsInsightDiario(
                midEmpId=conta.macEmpId,
                midMacId=conta.macId,
                midMcgId=mcg_id,
                midData=i.dia,
                midInvestimento=0,
                midImpressoes=0,
                midCliques=0,
                midAlcance=0,
                midLeadsMeta=0,
            )
            por_chave[(mcg_id, i.dia)] = linha
            db.add(linha)
        linha.midInvestimento = float(linha.midInvestimento) + float(i.investimento)
        linha.midImpressoes += i.impressoes
        linha.midCliques += i.cliques
        linha.midAlcance += i.alcance
        linha.midLeadsMeta += i.leads
    db.flush()
    return len(por_chave)


def _finalizar(
    db: Session,
    mac_id: int,
    resultado: ResultadoSync,
    inicio: date,
    fim: date,
    origem: str,
    duracao_ms: int,
    marcar_carga_inicial: bool,
) -> None:
    conta = db.get(MetaAdsConta, mac_id)
    conta.macStatus = resultado.status
    conta.macMensagem = resultado.erro[:500] if resultado.erro else None
    conta.macSyncIniciadaEm = None
    if resultado.status == STATUS_OK:
        conta.macUltimaSync = utcnow()
        if marcar_carga_inicial:
            conta.macCargaInicialFeita = True
    db.add(
        MetaAdsSyncLog(
            mslMacId=mac_id,
            mslInicio=inicio,
            mslFim=fim,
            mslOrigem=origem,
            mslStatus=STATUS_ERRO if resultado.status == STATUS_TOKEN_INVALIDO else resultado.status,
            mslLinhas=resultado.linhas,
            mslLeadsVinculados=resultado.leads_vinculados,
            mslErro=resultado.erro[:500] if resultado.erro else None,
            mslDuracaoMs=duracao_ms,
        )
    )
    db.commit()


def executar_em_sessao_propria(
    mac_id: int, origem: str, inicio: date | None = None, fim: date | None = None
) -> ResultadoSync:
    """Para BackgroundTasks e worker: a sessao da requisicao ja foi fechada."""
    from ...database import SessionLocal

    with SessionLocal() as db:
        return sincronizar_conta(db, mac_id, origem=origem, inicio=inicio, fim=fim)


def contas_da_rodada_diaria(db: Session) -> list[int]:
    return list(
        db.execute(
            select(MetaAdsConta.macId)
            .where(
                MetaAdsConta.macAtivo.is_(True),
                MetaAdsConta.macStatus != STATUS_TOKEN_INVALIDO,
            )
            .order_by(MetaAdsConta.macId)
        ).scalars()
    )


def sincronizar_todas_agendadas() -> int:
    """Rodada diaria. Uma conta com problema nao impede as demais. Devolve quantas rodaram."""
    from ...database import SessionLocal

    with SessionLocal() as db:
        ids = contas_da_rodada_diaria(db)
    rodadas = 0
    for mac_id in ids:
        try:
            with SessionLocal() as db:
                if reivindicar(db, mac_id):
                    sincronizar_conta(db, mac_id, origem="agendada")
                    rodadas += 1
        except Exception:
            logger.exception("Falha na rodada diaria Meta Ads da conta %s", mac_id)
    return rodadas
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_sincronizacao -v`
Expected: 16 testes OK.

- [ ] **Step 5: Commit**

```bash
git add backend/services/meta_ads/sincronizacao.py backend/tests/test_meta_ads_sincronizacao.py
git commit -m "Meta Ads: sincronização de conta com trava, janela e log

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Worker da rodada diária

**Files:**
- Create: `backend/workers/meta_ads_worker.py`
- Modify: `backend/main.py:44-56` (lifespan)
- Test: `backend/tests/test_meta_ads_worker.py`

**Interfaces:**
- Consumes: `sincronizacao.sincronizar_todas_agendadas()` (Task 5), `settings.META_ADS_SYNC_ENABLED`, `settings.META_ADS_SYNC_HORA`.
- Produces: `backend.workers.meta_ads_worker.segundos_ate_proxima(agora: datetime, hora: int) -> float`, `async iniciar() -> None`, `async parar() -> None`.

- [ ] **Step 1: Write the failing test** — `backend/tests/test_meta_ads_worker.py`

```python
import unittest
from datetime import datetime, timezone

from backend.workers import meta_ads_worker as w


class ProximaExecucaoTests(unittest.TestCase):
    def test_antes_da_hora_no_mesmo_dia(self) -> None:
        # 05:00 UTC = 02:00 em Sao Paulo; proxima 04:00 SP = daqui 2h.
        agora = datetime(2026, 10, 14, 5, 0, tzinfo=timezone.utc)
        self.assertEqual(w.segundos_ate_proxima(agora, 4), 2 * 3600)

    def test_depois_da_hora_vai_para_amanha(self) -> None:
        # 12:00 UTC = 09:00 SP; proxima 04:00 SP = 19h depois.
        agora = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(w.segundos_ate_proxima(agora, 4), 19 * 3600)

    def test_exatamente_na_hora_vai_para_amanha(self) -> None:
        agora = datetime(2026, 10, 14, 7, 0, tzinfo=timezone.utc)  # 04:00 SP
        self.assertEqual(w.segundos_ate_proxima(agora, 4), 24 * 3600)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_worker -v`
Expected: FAIL com `ImportError`.

- [ ] **Step 3: Implementar** — `backend/workers/meta_ads_worker.py`

```python
"""
Worker da sincronizacao diaria do Meta Ads: task asyncio iniciada no lifespan, no mesmo
modelo do webhook_worker (processo unico, trabalho pesado na threadpool).

So cuida da rodada agendada. O "Sincronizar agora" da tela roda em BackgroundTasks do
FastAPI, com a trava pega na propria requisicao.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from starlette.concurrency import run_in_threadpool

from ..config import settings

logger = logging.getLogger(__name__)

FUSO = ZoneInfo("America/Sao_Paulo")

_parar = asyncio.Event()
_task: asyncio.Task | None = None


def segundos_ate_proxima(agora: datetime, hora: int) -> float:
    """`agora` com fuso. Proxima ocorrencia de hora:00 em Sao Paulo, sempre no futuro."""
    local = agora.astimezone(FUSO)
    alvo = local.replace(hour=hora, minute=0, second=0, microsecond=0)
    if alvo <= local:
        alvo += timedelta(days=1)
    return (alvo - local).total_seconds()


def _ciclo() -> None:
    from ..services.meta_ads import sincronizacao

    rodadas = sincronizacao.sincronizar_todas_agendadas()
    logger.info("Meta Ads: rodada diaria concluida (%s contas)", rodadas)


async def _loop_principal() -> None:
    logger.info("Worker Meta Ads iniciado (rodada diaria as %sh)", settings.META_ADS_SYNC_HORA)
    while not _parar.is_set():
        espera = segundos_ate_proxima(datetime.now(timezone.utc), settings.META_ADS_SYNC_HORA)
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(_parar.wait(), timeout=espera)
        if _parar.is_set():
            break
        try:
            await run_in_threadpool(_ciclo)
        except Exception:
            logger.exception("Falha na rodada diaria do Meta Ads")
    logger.info("Worker Meta Ads encerrado")


async def iniciar() -> None:
    global _task
    if not settings.META_ADS_SYNC_ENABLED:
        logger.info("Worker Meta Ads desabilitado por configuracao")
        return
    _parar.clear()
    _task = asyncio.create_task(_loop_principal())


async def parar() -> None:
    global _task
    if _task is None:
        return
    _parar.set()
    with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
        await asyncio.wait_for(_task, timeout=10)
    _task = None
```

Em `backend/main.py`, trocar o corpo do `lifespan` por:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Sobe e desce os workers (webhooks e Meta Ads) e o servidor MCP junto com a aplicacao."""
    from .workers import meta_ads_worker, webhook_worker

    await webhook_worker.iniciar()
    await meta_ads_worker.iniciar()
    try:
        async with servidor_mcp.session_manager.run():
            logger.info("Servidor MCP disponível em /api/mcp/{chave}")
            yield
    finally:
        await meta_ads_worker.parar()
        await webhook_worker.parar()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_worker -v`
Expected: 3 testes OK.

- [ ] **Step 5: Commit**

```bash
git add backend/workers/meta_ads_worker.py backend/main.py backend/tests/test_meta_ads_worker.py
git commit -m "Meta Ads: worker da sincronização diária no lifespan

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: API de configuração das contas (admin)

**Files:**
- Create: `backend/schemas/meta_ads.py`, `backend/services/meta_ads/contas.py`, `backend/routers/meta_ads_router.py`
- Modify: `backend/main.py` (import e `app.include_router(meta_ads_router.router)` depois de `webhook_router`)
- Test: `backend/tests/test_meta_ads_contas.py`, `backend/tests/test_meta_ads_router.py`

**Interfaces:**
- Consumes: `cripto.cifrar/decifrar`, `cliente_graph.normalizar_conta/ClienteGraph/MetaGraphErro`, `sincronizacao.reivindicar/executar_em_sessao_propria/MAX_DIAS_PERIODO`, constantes de status.
- Produces:
  - Schemas em `backend.schemas.meta_ads`: `MetaAdsContaCreate`, `MetaAdsContaUpdate`, `MetaAdsContaResponse`, `MetaAdsContaListResponse`, `MetaAdsTesteResponse`, `MetaAdsSyncLogResponse`, `MetaAdsSyncLogListResponse`, `MetaAdsSyncPeriodoRequest`, `MetaAdsSyncIniciadaResponse` (campos abaixo).
  - Em `backend.services.meta_ads.contas`: `obter_conta_da_empresa(db, emp_id, mac_id) -> MetaAdsConta`, `listar_contas(db, emp_id) -> MetaAdsContaListResponse`, `criar_conta(db, emp_id, data) -> MetaAdsContaResponse`, `atualizar_conta(db, emp_id, mac_id, data) -> MetaAdsContaResponse`, `testar_conta(db, emp_id, mac_id, fabrica_cliente=ClienteGraph) -> MetaAdsTesteResponse`, `listar_logs(db, emp_id, mac_id, limite=30) -> MetaAdsSyncLogListResponse`, `ids_contas_ativas(db, emp_id, mac_id: int | None) -> list[int]`.
  - Em `backend.routers.meta_ads_router`: `router` (prefixo `/api/meta-ads`) e o helper `empresa_obrigatoria(db, current_user, company_id) -> int` (reusado na Task 8).

- [ ] **Step 1: Criar os schemas** — `backend/schemas/meta_ads.py`

```python
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class MetaAdsContaCreate(BaseModel):
    macNome: str = Field(min_length=1, max_length=150)
    macContaExterna: str = Field(min_length=1, max_length=40)
    token: str = Field(min_length=20, max_length=2000)
    origens: list[int] = Field(default_factory=list)

    @field_validator("token")
    @classmethod
    def _sem_espacos(cls, valor: str) -> str:
        # Token copiado do Business Manager costuma vir com espaco ou quebra de linha.
        return "".join(valor.split())


class MetaAdsContaUpdate(BaseModel):
    macNome: str | None = Field(default=None, min_length=1, max_length=150)
    token: str | None = Field(default=None, min_length=20, max_length=2000)
    origens: list[int] | None = None
    macAtivo: bool | None = None

    @field_validator("token")
    @classmethod
    def _sem_espacos(cls, valor: str | None) -> str | None:
        return "".join(valor.split()) if valor is not None else None


class MetaAdsContaResponse(BaseModel):
    macId: int
    macNome: str
    macContaExterna: str
    macTokenFinal: str
    macMoeda: str | None
    macFuso: str | None
    macStatus: str
    macMensagem: str | None
    macUltimaSync: datetime | None
    macCargaInicialFeita: bool
    macAtivo: bool
    origens: list[int]


class MetaAdsContaListResponse(BaseModel):
    items: list[MetaAdsContaResponse]


class MetaAdsTesteResponse(BaseModel):
    ok: bool
    nome: str | None = None
    moeda: str | None = None
    fuso: str | None = None
    mensagem: str | None = None


class MetaAdsSyncLogResponse(BaseModel):
    mslId: int
    mslInicio: date
    mslFim: date
    mslOrigem: str
    mslStatus: str
    mslLinhas: int
    mslLeadsVinculados: int
    mslErro: str | None
    mslDuracaoMs: int | None
    mslDataExecucao: datetime

    class Config:
        from_attributes = True


class MetaAdsSyncLogListResponse(BaseModel):
    items: list[MetaAdsSyncLogResponse]


class MetaAdsSyncPeriodoRequest(BaseModel):
    data_inicial: date
    data_final: date
    macId: int | None = None

    @model_validator(mode="after")
    def _periodo_valido(self):
        from ..services.meta_ads.sincronizacao import MAX_DIAS_PERIODO

        if self.data_final < self.data_inicial:
            raise ValueError("A data final deve ser igual ou posterior à inicial")
        if (self.data_final - self.data_inicial).days > MAX_DIAS_PERIODO:
            raise ValueError(f"O período pode ter no máximo {MAX_DIAS_PERIODO} dias")
        return self


class MetaAdsSyncIniciadaResponse(BaseModel):
    contas: list[int]
    mensagem: str
```

- [ ] **Step 2: Write the failing test do serviço** — `backend/tests/test_meta_ads_contas.py`

```python
import unittest

from backend.core.cripto import decifrar
from backend.exceptions import BadRequestError, ConflictError, NotFoundError
from backend.models.meta_ads_conta import STATUS_PENDENTE, STATUS_TOKEN_INVALIDO, MetaAdsConta
from backend.schemas.meta_ads import MetaAdsContaCreate, MetaAdsContaUpdate
from backend.services.meta_ads import cliente_graph as g
from backend.services.meta_ads import contas
from backend.tests import banco_sqlite as b

TOKEN = "EAABsbCS1iHgBO-token-de-teste-9876"


class FabricaFalsa:
    def __init__(self, conta=None, erro=None):
        self.conta, self.erro = conta, erro

    def __call__(self, token):
        self.token = token
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def obter_conta(self, act):
        if self.erro:
            raise self.erro
        return self.conta


class ContasTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.origem = b.criar_origem(self.db, self.emp.empId, "Anúncios")

    def _criar(self, **kw):
        dados = dict(macNome="Conta principal", macContaExterna="act_123", token=TOKEN, origens=[self.origem.ccoId])
        dados.update(kw)
        return contas.criar_conta(self.db, self.emp.empId, MetaAdsContaCreate(**dados))

    def test_cria_com_token_cifrado_e_nunca_devolvido(self) -> None:
        resp = self._criar(macContaExterna="123")
        self.assertEqual(resp.macContaExterna, "act_123")
        self.assertEqual(resp.macTokenFinal, "9876")
        self.assertEqual(resp.origens, [self.origem.ccoId])
        self.assertEqual(resp.macStatus, STATUS_PENDENTE)
        self.assertNotIn(TOKEN, resp.model_dump_json())
        conta = self.db.get(MetaAdsConta, resp.macId)
        self.assertNotEqual(conta.macToken, TOKEN)
        self.assertEqual(decifrar(conta.macToken), TOKEN)

    def test_token_e_normalizado(self) -> None:
        resp = self._criar(token=f"  {TOKEN[:10]}\n{TOKEN[10:]}  ")
        self.assertEqual(decifrar(self.db.get(MetaAdsConta, resp.macId).macToken), TOKEN)

    def test_conta_duplicada(self) -> None:
        self._criar()
        with self.assertRaises(ConflictError):
            self._criar(macContaExterna="act_123")

    def test_conta_vazia(self) -> None:
        with self.assertRaises(BadRequestError):
            self._criar(macContaExterna="act_")

    def test_origem_de_outra_empresa_recusada(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        origem_outra = b.criar_origem(self.db, outra.empId, "Anúncios")
        with self.assertRaises(BadRequestError):
            self._criar(origens=[origem_outra.ccoId])

    def test_conta_de_outra_empresa_nao_encontrada(self) -> None:
        resp = self._criar()
        outra = b.criar_empresa(self.db, "Outra")
        with self.assertRaises(NotFoundError):
            contas.obter_conta_da_empresa(self.db, outra.empId, resp.macId)

    def test_trocar_token_volta_para_pendente(self) -> None:
        resp = self._criar()
        conta = self.db.get(MetaAdsConta, resp.macId)
        conta.macStatus, conta.macMensagem = STATUS_TOKEN_INVALIDO, "Token inválido"
        self.db.commit()
        novo = "EAAB-outro-token-de-teste-5555"
        resp = contas.atualizar_conta(self.db, self.emp.empId, resp.macId, MetaAdsContaUpdate(token=novo))
        self.assertEqual((resp.macStatus, resp.macMensagem, resp.macTokenFinal), (STATUS_PENDENTE, None, "5555"))

    def test_atualiza_origens_e_ativo(self) -> None:
        resp = self._criar()
        resp = contas.atualizar_conta(
            self.db, self.emp.empId, resp.macId, MetaAdsContaUpdate(origens=[], macAtivo=False)
        )
        self.assertEqual((resp.origens, resp.macAtivo), ([], False))

    def test_testar_conexao_ok_grava_moeda_e_fuso(self) -> None:
        resp = self._criar()
        fab = FabricaFalsa(conta=g.ContaMeta("Conta no Meta", "BRL", "America/Sao_Paulo"))
        r = contas.testar_conta(self.db, self.emp.empId, resp.macId, fabrica_cliente=fab)
        self.assertEqual((r.ok, r.nome, r.moeda), (True, "Conta no Meta", "BRL"))
        self.assertEqual(fab.token, TOKEN)
        self.assertEqual(self.db.get(MetaAdsConta, resp.macId).macFuso, "America/Sao_Paulo")

    def test_testar_conexao_com_erro_devolve_mensagem(self) -> None:
        resp = self._criar()
        fab = FabricaFalsa(erro=g.TokenInvalidoErro("Token inválido", 190))
        r = contas.testar_conta(self.db, self.emp.empId, resp.macId, fabrica_cliente=fab)
        self.assertEqual((r.ok, r.mensagem), (False, "Token inválido"))

    def test_listar_e_ids_ativos(self) -> None:
        a = self._criar(macContaExterna="act_1")
        bconta = self._criar(macContaExterna="act_2")
        contas.atualizar_conta(self.db, self.emp.empId, bconta.macId, MetaAdsContaUpdate(macAtivo=False))
        self.assertEqual(len(contas.listar_contas(self.db, self.emp.empId).items), 2)
        self.assertEqual(contas.ids_contas_ativas(self.db, self.emp.empId, None), [a.macId])
        self.assertEqual(contas.ids_contas_ativas(self.db, self.emp.empId, bconta.macId), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_contas -v`
Expected: FAIL com `ImportError: cannot import name 'contas'`.

- [ ] **Step 4: Implementar o serviço** — `backend/services/meta_ads/contas.py`

```python
"""Cadastro das contas do Meta Ads de uma empresa, teste de conexao e log de sincronizacao."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ...core.cripto import cifrar, decifrar
from ...exceptions import BadRequestError, ConflictError, NotFoundError
from ...models.como_conheceu import ComoConheceu
from ...models.meta_ads_conta import STATUS_PENDENTE, STATUS_TOKEN_INVALIDO, MetaAdsConta
from ...models.meta_ads_conta_origem import MetaAdsContaOrigem
from ...models.meta_ads_sync_log import MetaAdsSyncLog
from ...schemas.meta_ads import (
    MetaAdsContaCreate,
    MetaAdsContaListResponse,
    MetaAdsContaResponse,
    MetaAdsContaUpdate,
    MetaAdsSyncLogListResponse,
    MetaAdsSyncLogResponse,
    MetaAdsTesteResponse,
)
from .cliente_graph import ClienteGraph, MetaGraphErro, normalizar_conta


def _origens(db: Session, mac_id: int) -> list[int]:
    return sorted(
        db.execute(
            select(MetaAdsContaOrigem.mcoCcoId).where(MetaAdsContaOrigem.mcoMacId == mac_id)
        ).scalars()
    )


def _resposta(db: Session, conta: MetaAdsConta) -> MetaAdsContaResponse:
    return MetaAdsContaResponse(
        macId=conta.macId,
        macNome=conta.macNome,
        macContaExterna=conta.macContaExterna,
        macTokenFinal=conta.macTokenFinal,
        macMoeda=conta.macMoeda,
        macFuso=conta.macFuso,
        macStatus=conta.macStatus,
        macMensagem=conta.macMensagem,
        macUltimaSync=conta.macUltimaSync,
        macCargaInicialFeita=conta.macCargaInicialFeita,
        macAtivo=conta.macAtivo,
        origens=_origens(db, conta.macId),
    )


def obter_conta_da_empresa(db: Session, emp_id: int, mac_id: int) -> MetaAdsConta:
    conta = db.get(MetaAdsConta, mac_id)
    if conta is None or conta.macEmpId != emp_id:
        raise NotFoundError("Conta de anúncios não encontrada")
    return conta


def _validar_origens(db: Session, emp_id: int, ids: list[int]) -> list[int]:
    unicos = sorted(set(ids))
    if not unicos:
        return []
    encontrados = db.execute(
        select(func.count(ComoConheceu.ccoId)).where(
            ComoConheceu.ccoEmpId == emp_id, ComoConheceu.ccoId.in_(unicos)
        )
    ).scalar_one()
    if encontrados != len(unicos):
        raise BadRequestError("Origem inválida para esta empresa")
    return unicos


def _definir_origens(db: Session, conta: MetaAdsConta, ids: list[int]) -> None:
    db.execute(delete(MetaAdsContaOrigem).where(MetaAdsContaOrigem.mcoMacId == conta.macId))
    for cco_id in ids:
        db.add(MetaAdsContaOrigem(mcoMacId=conta.macId, mcoCcoId=cco_id))


def listar_contas(db: Session, emp_id: int) -> MetaAdsContaListResponse:
    lista = db.execute(
        select(MetaAdsConta).where(MetaAdsConta.macEmpId == emp_id).order_by(MetaAdsConta.macNome)
    ).scalars()
    return MetaAdsContaListResponse(items=[_resposta(db, c) for c in lista])


def criar_conta(db: Session, emp_id: int, data: MetaAdsContaCreate) -> MetaAdsContaResponse:
    try:
        act = normalizar_conta(data.macContaExterna)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    origens = _validar_origens(db, emp_id, data.origens)
    existe = db.execute(
        select(MetaAdsConta.macId).where(
            MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macContaExterna == act
        )
    ).first()
    if existe:
        raise ConflictError("Esta conta de anúncios já está cadastrada nesta empresa")
    conta = MetaAdsConta(
        macEmpId=emp_id,
        macNome=data.macNome.strip(),
        macContaExterna=act,
        macToken=cifrar(data.token),
        macTokenFinal=data.token[-4:],
        macStatus=STATUS_PENDENTE,
    )
    db.add(conta)
    db.flush()
    _definir_origens(db, conta, origens)
    db.commit()
    return _resposta(db, conta)


def atualizar_conta(
    db: Session, emp_id: int, mac_id: int, data: MetaAdsContaUpdate
) -> MetaAdsContaResponse:
    conta = obter_conta_da_empresa(db, emp_id, mac_id)
    if data.macNome is not None:
        conta.macNome = data.macNome.strip()
    if data.token is not None:
        conta.macToken = cifrar(data.token)
        conta.macTokenFinal = data.token[-4:]
        conta.macStatus = STATUS_PENDENTE
        conta.macMensagem = None
    if data.origens is not None:
        _definir_origens(db, conta, _validar_origens(db, emp_id, data.origens))
    if data.macAtivo is not None:
        conta.macAtivo = data.macAtivo
    db.commit()
    return _resposta(db, conta)


def testar_conta(
    db: Session, emp_id: int, mac_id: int, fabrica_cliente=ClienteGraph
) -> MetaAdsTesteResponse:
    conta = obter_conta_da_empresa(db, emp_id, mac_id)
    token = decifrar(conta.macToken)
    if token is None:
        return MetaAdsTesteResponse(
            ok=False, mensagem="Token ilegível (a chave de criptografia mudou) — cadastre o token de novo."
        )
    try:
        with fabrica_cliente(token) as cliente:
            info = cliente.obter_conta(conta.macContaExterna)
    except MetaGraphErro as exc:
        return MetaAdsTesteResponse(ok=False, mensagem=exc.mensagem)
    conta.macMoeda = info.moeda
    conta.macFuso = info.fuso
    if conta.macStatus == STATUS_TOKEN_INVALIDO:
        conta.macStatus = STATUS_PENDENTE
        conta.macMensagem = None
    db.commit()
    return MetaAdsTesteResponse(ok=True, nome=info.nome, moeda=info.moeda, fuso=info.fuso)


def listar_logs(db: Session, emp_id: int, mac_id: int, limite: int = 30) -> MetaAdsSyncLogListResponse:
    obter_conta_da_empresa(db, emp_id, mac_id)
    linhas = db.execute(
        select(MetaAdsSyncLog)
        .where(MetaAdsSyncLog.mslMacId == mac_id)
        .order_by(MetaAdsSyncLog.mslId.desc())
        .limit(limite)
    ).scalars()
    return MetaAdsSyncLogListResponse(items=[MetaAdsSyncLogResponse.model_validate(l) for l in linhas])


def ids_contas_ativas(db: Session, emp_id: int, mac_id: int | None) -> list[int]:
    stmt = select(MetaAdsConta.macId).where(
        MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True)
    )
    if mac_id is not None:
        stmt = stmt.where(MetaAdsConta.macId == mac_id)
    return list(db.execute(stmt.order_by(MetaAdsConta.macId)).scalars())
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_contas -v`
Expected: 11 testes OK.

- [ ] **Step 6: Write the failing test das rotas** — `backend/tests/test_meta_ads_router.py`

```python
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import get_current_user
from backend.database import get_db
from backend.routers import meta_ads_router
from backend.tests import banco_sqlite as b

TOKEN = "EAAB-token-de-teste-rotas-4321"


class RotasTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.usuario = SimpleNamespace(usuId=1, usuAdmin=True)
        app = FastAPI()
        app.include_router(meta_ads_router.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.usuario
        self.http = TestClient(app)
        self.h = {"X-Company-Id": str(self.emp.empId)}

    def _criar(self):
        r = self.http.post(
            "/api/meta-ads/contas",
            headers=self.h,
            json={"macNome": "Conta", "macContaExterna": "act_9", "token": TOKEN, "origens": []},
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def test_criar_e_listar_sem_token(self) -> None:
        self._criar()
        r = self.http.get("/api/meta-ads/contas", headers=self.h)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(TOKEN, r.text)
        self.assertEqual(r.json()["items"][0]["macTokenFinal"], "4321")

    def test_nao_admin_bloqueado(self) -> None:
        self.usuario.usuAdmin = False
        r = self.http.get("/api/meta-ads/contas", headers=self.h)
        self.assertEqual(r.status_code, 403)

    def test_sincronizar_duas_vezes_da_409(self) -> None:
        conta = self._criar()
        with patch.object(meta_ads_router.sincronizacao, "executar_em_sessao_propria") as rodar:
            r1 = self.http.post(f"/api/meta-ads/contas/{conta['macId']}/sincronizar", headers=self.h)
            r2 = self.http.post(f"/api/meta-ads/contas/{conta['macId']}/sincronizar", headers=self.h)
        self.assertEqual(r1.status_code, 202, r1.text)
        self.assertEqual(r2.status_code, 409)
        rodar.assert_called_once_with(conta["macId"], "manual")

    def test_periodo_invalido_da_422(self) -> None:
        r = self.http.post(
            "/api/meta-ads/sincronizar-periodo",
            headers=self.h,
            json={"data_inicial": "2026-10-10", "data_final": "2026-10-01"},
        )
        self.assertEqual(r.status_code, 422)

    def test_periodo_dispara_para_contas_ativas(self) -> None:
        conta = self._criar()
        with patch.object(meta_ads_router.sincronizacao, "executar_em_sessao_propria") as rodar:
            r = self.http.post(
                "/api/meta-ads/sincronizar-periodo",
                headers=self.h,
                json={"data_inicial": "2026-09-01", "data_final": "2026-09-30"},
            )
        self.assertEqual(r.status_code, 202, r.text)
        self.assertEqual(r.json()["contas"], [conta["macId"]])
        args = rodar.call_args.args
        self.assertEqual((args[0], args[1], str(args[2]), str(args[3])), (conta["macId"], "periodo", "2026-09-01", "2026-09-30"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 7: Run test to verify it fails**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_router -v`
Expected: FAIL com `ImportError: cannot import name 'meta_ads_router'`.

- [ ] **Step 8: Implementar o router** — `backend/routers/meta_ads_router.py`

```python
"""
Meta Ads: configuracao das contas (admin) e, na Task 8, indicadores das campanhas.

Rotas internas em portugues, JWT + X-Company-Id. Toda rota exige empresa selecionada.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, status

from ..dependencies import (
    CompanyIdDep,
    CurrentUserDep,
    DbSessionDep,
    require_admin,
    require_user_in_company,
)
from ..exceptions import BadRequestError, ConflictError
from ..schemas.meta_ads import (
    MetaAdsContaCreate,
    MetaAdsContaListResponse,
    MetaAdsContaResponse,
    MetaAdsContaUpdate,
    MetaAdsSyncIniciadaResponse,
    MetaAdsSyncLogListResponse,
    MetaAdsSyncPeriodoRequest,
    MetaAdsTesteResponse,
)
from ..services.meta_ads import contas, sincronizacao

router = APIRouter(prefix="/api/meta-ads", tags=["meta-ads"])


def empresa_obrigatoria(db, current_user, company_id) -> int:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    if company_id is None:
        raise BadRequestError("Selecione uma empresa")
    return company_id


def _admin(db, current_user, company_id) -> int:
    require_admin(current_user)
    return empresa_obrigatoria(db, current_user, company_id)


@router.get("/contas", response_model=MetaAdsContaListResponse)
def listar_contas(
    db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsContaListResponse:
    return contas.listar_contas(db, _admin(db, current_user, company_id))


@router.post("/contas", response_model=MetaAdsContaResponse, status_code=status.HTTP_201_CREATED)
def criar_conta(
    data: MetaAdsContaCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MetaAdsContaResponse:
    return contas.criar_conta(db, _admin(db, current_user, company_id), data)


@router.put("/contas/{mac_id}", response_model=MetaAdsContaResponse)
def atualizar_conta(
    mac_id: int,
    data: MetaAdsContaUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MetaAdsContaResponse:
    return contas.atualizar_conta(db, _admin(db, current_user, company_id), mac_id, data)


@router.post("/contas/{mac_id}/testar", response_model=MetaAdsTesteResponse)
def testar_conta(
    mac_id: int, db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsTesteResponse:
    return contas.testar_conta(db, _admin(db, current_user, company_id), mac_id)


@router.post(
    "/contas/{mac_id}/sincronizar",
    response_model=MetaAdsSyncIniciadaResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def sincronizar_conta(
    mac_id: int,
    tarefas: BackgroundTasks,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MetaAdsSyncIniciadaResponse:
    conta = contas.obter_conta_da_empresa(db, _admin(db, current_user, company_id), mac_id)
    if not sincronizacao.reivindicar(db, conta.macId):
        raise ConflictError("Sincronização já em andamento para esta conta (ou conta inativa)")
    tarefas.add_task(sincronizacao.executar_em_sessao_propria, conta.macId, "manual")
    return MetaAdsSyncIniciadaResponse(contas=[conta.macId], mensagem="Sincronização iniciada")


@router.post(
    "/sincronizar-periodo",
    response_model=MetaAdsSyncIniciadaResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def sincronizar_periodo(
    data: MetaAdsSyncPeriodoRequest,
    tarefas: BackgroundTasks,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MetaAdsSyncIniciadaResponse:
    emp_id = _admin(db, current_user, company_id)
    disparadas: list[int] = []
    for mac_id in contas.ids_contas_ativas(db, emp_id, data.macId):
        if sincronizacao.reivindicar(db, mac_id):
            tarefas.add_task(
                sincronizacao.executar_em_sessao_propria,
                mac_id,
                "periodo",
                data.data_inicial,
                data.data_final,
            )
            disparadas.append(mac_id)
    if not disparadas:
        raise ConflictError("Nenhuma conta ativa livre para sincronizar agora")
    return MetaAdsSyncIniciadaResponse(contas=disparadas, mensagem="Reprocessamento iniciado")


@router.get("/contas/{mac_id}/logs", response_model=MetaAdsSyncLogListResponse)
def listar_logs(
    mac_id: int, db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsSyncLogListResponse:
    return contas.listar_logs(db, _admin(db, current_user, company_id), mac_id)
```

Em `backend/main.py`: adicionar `meta_ads_router,` à lista de imports de `.routers` (ordem alfabética, depois de `llm_agente_router`) e `app.include_router(meta_ads_router.router)` depois de `app.include_router(webhook_router.router)`.

- [ ] **Step 9: Run tests to verify they pass**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_contas backend.tests.test_meta_ads_router -v`
Expected: 16 testes OK. (Se `test_nao_admin_bloqueado` der 400 em vez de 403, conferir que `_admin` chama `require_admin` antes de `empresa_obrigatoria`.)

- [ ] **Step 10: Commit**

```bash
git add backend/schemas/meta_ads.py backend/services/meta_ads/contas.py backend/routers/meta_ads_router.py backend/main.py backend/tests/test_meta_ads_contas.py backend/tests/test_meta_ads_router.py
git commit -m "Meta Ads: API de contas, teste de conexão e sincronização manual

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Indicadores, rotas de leitura e vínculo manual

**Files:**
- Modify: `backend/services/crm_dashboard_service.py:1305-1337` (extrair `condicoes_periodo`), `backend/schemas/meta_ads.py` (schemas de leitura), `backend/routers/meta_ads_router.py` (rotas de leitura)
- Create: `backend/services/meta_ads/indicadores.py`
- Test: `backend/tests/test_meta_ads_indicadores.py`

**Interfaces:**
- Consumes: `crm_dashboard_service._between_dates`, `_mrr_incremental_expr`, `_valor_projeto_expr`; models; `empresa_obrigatoria` (Task 7).
- Produces:
  - Em `backend.services.crm_dashboard_service`: `@dataclass(frozen=True) CondicoesPeriodo(recebidas, ganhas, perdidas, ativas, escopo)` e `condicoes_periodo(data_inicial: date | None, data_final: date | None) -> CondicoesPeriodo`.
  - Schemas: `MetaAdsLinha`, `MetaAdsPainelResponse`, `MetaAdsSerieDia`, `MetaAdsLeadItem`, `MetaAdsCampanhaDetalheResponse`, `MetaAdsResumoResponse`, `MetaAdsCampanhaOpcao`, `MetaAdsCampanhaOpcoesResponse`, `MetaAdsContaOpcao`, `MetaAdsContaOpcoesResponse`, `OportunidadeCampanhaMetaRequest`, `OportunidadeCampanhaMetaResponse`.
  - Em `backend.services.meta_ads.indicadores`: `@dataclass(frozen=True) FiltroPainel(data_inicial, data_final, mac_id=None, somente_ativas=False)`, `calcular_derivados(...) -> dict`, `tem_conta(db, emp_id) -> bool`, `painel(db, emp_id, filtro) -> MetaAdsPainelResponse`, `detalhe_campanha(db, emp_id, mcg_id, data_inicial, data_final) -> MetaAdsCampanhaDetalheResponse`, `resumo(db, emp_id, data_inicial, data_final) -> MetaAdsResumoResponse`, `opcoes_campanhas(db, emp_id) -> MetaAdsCampanhaOpcoesResponse`, `opcoes_contas(db, emp_id) -> MetaAdsContaOpcoesResponse`, `definir_campanha_oportunidade(db, emp_id, opo_id, mcg_id) -> OportunidadeCampanhaMetaResponse`.
  - Rotas: `GET /api/meta-ads/painel`, `GET /api/meta-ads/campanhas/{mcg_id}`, `GET /api/meta-ads/resumo`, `GET /api/meta-ads/campanhas-opcoes`, `GET /api/meta-ads/contas-opcoes`, `PATCH /api/meta-ads/oportunidades/{opo_id}/campanha`.

- [ ] **Step 1: Extrair `condicoes_periodo` (refatoração sem mudança de comportamento)**

Em `backend/services/crm_dashboard_service.py`, adicionar `from dataclasses import dataclass` e `from typing import Any` aos imports e, logo antes de `def _ranking_base_where`, a função:

```python
@dataclass(frozen=True)
class CondicoesPeriodo:
    """Condicoes de periodo das abas de ranking. Reusadas pelo Meta Ads para os numeros baterem."""

    recebidas: Any
    ganhas: Any
    perdidas: Any
    ativas: Any
    escopo: Any


def condicoes_periodo(data_inicial: Optional[date], data_final: Optional[date]) -> CondicoesPeriodo:
    bd_rec = _between_dates(Oportunidade.opoDataRecebimento, data_inicial, data_final)
    bd_fec = _between_dates(Oportunidade.opoDataFechamento, data_inicial, data_final)
    perd_ref = func.coalesce(Oportunidade.opoDataFechamento, Oportunidade.opoDataRecebimento)
    bd_perd = _between_dates(perd_ref, data_inicial, data_final)
    rec_date = bd_rec if bd_rec is not None else true()
    fec_date = bd_fec if bd_fec is not None else true()
    perd_date = bd_perd if bd_perd is not None else true()

    rec_cond = and_(
        Oportunidade.opoAtivo.is_(True),
        Oportunidade.opoDataRecebimento.isnot(None),
        rec_date,
    )
    gan_cond = and_(
        Oportunidade.opoAtivo.is_(True),
        Oportunidade.opoStatusFechamento == "ganho",
        Oportunidade.opoDataFechamento.isnot(None),
        fec_date,
    )
    perd_cond = and_(
        Oportunidade.opoAtivo.is_(True),
        Oportunidade.opoStatusFechamento == "perdido",
        perd_ref.isnot(None),
        perd_date,
    )
    atv_cond = and_(Oportunidade.opoAtivo.is_(True), Oportunidade.opoStatusFechamento.is_(None))
    return CondicoesPeriodo(
        recebidas=rec_cond,
        ganhas=gan_cond,
        perdidas=perd_cond,
        ativas=atv_cond,
        escopo=or_(rec_cond, gan_cond, perd_cond, atv_cond),
    )
```

Em `_query_rankings_analiticos`, substituir as linhas de `di, df = ...` até `scope = or_(...)` (1310–1337) por:

```python
    cond = condicoes_periodo(filtros.data_inicial, filtros.data_final)
    rec_cond, gan_cond, perd_cond, atv_cond, scope = (
        cond.recebidas,
        cond.ganhas,
        cond.perdidas,
        cond.ativas,
        cond.escopo,
    )
```

Run: `.venv/Scripts/python -m unittest backend.tests.test_crm_dashboard_service backend.tests.test_crm_dashboard_router backend.tests.test_mcp_ferramentas_indicadores -v`
Expected: todos OK.

- [ ] **Step 2: Adicionar os schemas de leitura** — no fim de `backend/schemas/meta_ads.py`

```python
class MetaAdsLinha(BaseModel):
    mcgId: int | None
    nome: str
    status: str | None
    macId: int | None
    investimento: float
    impressoes: int
    cliques: int
    leadsMeta: int
    leadsCrm: int
    vendas: int
    mrr: float
    projeto: float
    ctr: float | None
    cpc: float | None
    cpl: float | None
    cac: float | None
    retorno: float | None


class MetaAdsPainelResponse(BaseModel):
    temConta: bool
    total: MetaAdsLinha
    campanhas: list[MetaAdsLinha]
    naoIdentificada: MetaAdsLinha | None


class MetaAdsSerieDia(BaseModel):
    data: date
    investimento: float
    leadsMeta: int
    leadsCrm: int


class MetaAdsLeadItem(BaseModel):
    opoId: int
    opoTitulo: str
    opoNomeContato: str | None
    opoDataRecebimento: date | None
    opoStatusFechamento: str | None
    opoValorFechado: float | None


class MetaAdsCampanhaDetalheResponse(BaseModel):
    campanha: MetaAdsLinha
    serie: list[MetaAdsSerieDia]
    leads: list[MetaAdsLeadItem]


class MetaAdsResumoResponse(BaseModel):
    temConta: bool
    investimento: float
    leadsCrm: int
    vendas: int
    cpl: float | None
    cac: float | None
    retorno: float | None


class MetaAdsCampanhaOpcao(BaseModel):
    mcgId: int
    nome: str
    conta: str
    status: str | None


class MetaAdsCampanhaOpcoesResponse(BaseModel):
    items: list[MetaAdsCampanhaOpcao]


class MetaAdsContaOpcao(BaseModel):
    macId: int
    macNome: str


class MetaAdsContaOpcoesResponse(BaseModel):
    items: list[MetaAdsContaOpcao]


class OportunidadeCampanhaMetaRequest(BaseModel):
    opoMcgId: int | None


class OportunidadeCampanhaMetaResponse(BaseModel):
    opoId: int
    opoMcgId: int | None
    opoMcgManual: bool
```

- [ ] **Step 3: Write the failing test** — `backend/tests/test_meta_ads_indicadores.py`

```python
import unittest
from datetime import date

from backend.exceptions import BadRequestError, NotFoundError
from backend.schemas.crm_dashboard import CrmDashboardFiltroParams
from backend.services.crm_dashboard_service import _query_rankings_analiticos
from backend.services.meta_ads import indicadores as ind
from backend.tests import banco_sqlite as b

INI, FIM = date(2026, 10, 1), date(2026, 10, 31)


class DerivadosTests(unittest.TestCase):
    def test_divisoes_por_zero_viram_none(self) -> None:
        d = ind.calcular_derivados(investimento=0, leads=0, vendas=0, mrr=0, projeto=0, impressoes=0, cliques=0)
        self.assertEqual(d, {"ctr": None, "cpc": None, "cpl": None, "cac": None, "retorno": None})

    def test_formulas(self) -> None:
        d = ind.calcular_derivados(investimento=300, leads=2, vendas=1, mrr=1000, projeto=600, impressoes=2000, cliques=50)
        self.assertEqual(d, {"ctr": 2.5, "cpc": 6.0, "cpl": 150.0, "cac": 300.0, "retorno": 42.0})


class PainelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.anuncios = b.criar_origem(self.db, self.emp.empId, "Anúncios")
        self.indicacao = b.criar_origem(self.db, self.emp.empId, "Indicação")
        self.conta = b.criar_conta(self.db, self.emp.empId, origens=[self.anuncios.ccoId])
        self.c1 = b.criar_campanha(self.db, self.conta, "1", "Campanha 1")
        self.c2 = b.criar_campanha(self.db, self.conta, "2", "Campanha 2", status="PAUSED")
        b.criar_insight(self.db, self.c1, date(2026, 10, 2), 100, impressoes=1000, cliques=20, leads=3)
        b.criar_insight(self.db, self.c1, date(2026, 10, 3), 200, impressoes=1000, cliques=30, leads=1)
        b.criar_insight(self.db, self.c2, date(2026, 10, 3), 100)
        b.criar_insight(self.db, self.c1, date(2026, 9, 30), 999)  # fora do periodo
        cco = self.anuncios.ccoId
        # A: ligada a c1, recebida e ganha no periodo (MRR 1000)
        b.criar_oportunidade(
            self.db, self.emp.empId, opoCcoId=cco, opoMcgId=self.c1.mcgId,
            opoDataRecebimento=date(2026, 10, 5), opoStatusFechamento="ganho",
            opoDataFechamento=date(2026, 10, 20), opoValorFechado=1000, opoFechadoRecorrencia=0,
        )
        # B: ligada a c1, recebida, aberta
        b.criar_oportunidade(self.db, self.emp.empId, opoCcoId=cco, opoMcgId=self.c1.mcgId, opoDataRecebimento=date(2026, 10, 6))
        # C: origem Anuncios sem campanha, recebida e perdida
        b.criar_oportunidade(
            self.db, self.emp.empId, opoCcoId=cco, opoDataRecebimento=date(2026, 10, 7),
            opoStatusFechamento="perdido", opoDataFechamento=date(2026, 10, 8),
        )
        # D: outra origem, sem campanha -> nao e Meta
        b.criar_oportunidade(self.db, self.emp.empId, opoCcoId=self.indicacao.ccoId, opoDataRecebimento=date(2026, 10, 7))
        # E: outra empresa
        outra = b.criar_empresa(self.db, "Outra")
        b.criar_oportunidade(self.db, outra.empId, opoDataRecebimento=date(2026, 10, 7))

    def _painel(self, **kw):
        return ind.painel(self.db, self.emp.empId, ind.FiltroPainel(INI, FIM, **kw))

    def test_linhas_por_campanha(self) -> None:
        p = self._painel()
        self.assertTrue(p.temConta)
        por_id = {l.mcgId: l for l in p.campanhas}
        c1 = por_id[self.c1.mcgId]
        self.assertEqual(
            (c1.investimento, c1.leadsMeta, c1.leadsCrm, c1.vendas, c1.mrr, c1.cpl, c1.cac, c1.retorno),
            (300.0, 4, 2, 1, 1000.0, 150.0, 300.0, 40.0),
        )
        c2 = por_id[self.c2.mcgId]
        self.assertEqual((c2.investimento, c2.leadsCrm, c2.cpl), (100.0, 0, None))
        self.assertEqual([l.mcgId for l in p.campanhas], [self.c1.mcgId, self.c2.mcgId])

    def test_nao_identificada_e_total(self) -> None:
        p = self._painel()
        self.assertEqual((p.naoIdentificada.leadsCrm, p.naoIdentificada.investimento), (1, 0.0))
        self.assertEqual(
            (p.total.investimento, p.total.leadsCrm, p.total.vendas, p.total.mrr, p.total.cpl),
            (400.0, 3, 1, 1000.0, 133.33),
        )

    def test_bate_com_a_aba_fontes(self) -> None:
        rankings = _query_rankings_analiticos(
            self.db, self.emp.empId, CrmDashboardFiltroParams(data_inicial=INI, data_final=FIM)
        )
        fonte = next(f for f in rankings.fontes if f.fonte == "Anúncios")
        total = self._painel().total
        self.assertEqual((total.leadsCrm, total.vendas, total.mrr), (fonte.recebidas, fonte.ganhas, fonte.mrrIncremental))

    def test_somente_ativas(self) -> None:
        p = self._painel(somente_ativas=True)
        self.assertEqual([l.mcgId for l in p.campanhas], [self.c1.mcgId])
        self.assertEqual(p.total.investimento, 300.0)

    def test_filtro_por_conta(self) -> None:
        outra = b.criar_conta(self.db, self.emp.empId, act="act_222")
        c3 = b.criar_campanha(self.db, outra, "3", "Campanha 3")
        b.criar_insight(self.db, c3, date(2026, 10, 3), 50)
        p = self._painel(mac_id=outra.macId)
        self.assertEqual([l.mcgId for l in p.campanhas], [c3.mcgId])
        self.assertIsNone(p.naoIdentificada)  # a conta nova nao tem origens mapeadas

    def test_periodo_vazio(self) -> None:
        p = ind.painel(self.db, self.emp.empId, ind.FiltroPainel(date(2030, 1, 1), date(2030, 1, 31)))
        self.assertEqual(p.campanhas, [])
        self.assertIsNone(p.naoIdentificada)
        self.assertEqual((p.total.investimento, p.total.cpl, p.total.retorno), (0.0, None, None))

    def test_empresa_sem_conta(self) -> None:
        outra = b.criar_empresa(self.db, "Sem conta")
        p = ind.painel(self.db, outra.empId, ind.FiltroPainel(INI, FIM))
        self.assertFalse(p.temConta)

    def test_resumo(self) -> None:
        r = ind.resumo(self.db, self.emp.empId, INI, FIM)
        self.assertEqual((r.temConta, r.investimento, r.leadsCrm, r.vendas, r.cac), (True, 400.0, 3, 1, 400.0))

    def test_detalhe_campanha(self) -> None:
        d = ind.detalhe_campanha(self.db, self.emp.empId, self.c1.mcgId, INI, FIM)
        self.assertEqual(d.campanha.investimento, 300.0)
        self.assertEqual(
            [(s.data, s.investimento, s.leadsMeta, s.leadsCrm) for s in d.serie],
            [
                (date(2026, 10, 2), 100.0, 3, 0),
                (date(2026, 10, 3), 200.0, 1, 0),
                (date(2026, 10, 5), 0.0, 0, 1),
                (date(2026, 10, 6), 0.0, 0, 1),
            ],
        )
        self.assertEqual(len(d.leads), 2)

    def test_detalhe_de_outra_empresa(self) -> None:
        outra = b.criar_empresa(self.db, "Outra 2")
        with self.assertRaises(NotFoundError):
            ind.detalhe_campanha(self.db, outra.empId, self.c1.mcgId, INI, FIM)

    def test_opcoes(self) -> None:
        nomes = [o.nome for o in ind.opcoes_campanhas(self.db, self.emp.empId).items]
        self.assertEqual(nomes, ["Campanha 1", "Campanha 2"])  # ativas primeiro
        self.assertEqual([c.macId for c in ind.opcoes_contas(self.db, self.emp.empId).items], [self.conta.macId])


class VinculoManualTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.conta = b.criar_conta(self.db, self.emp.empId)
        self.camp = b.criar_campanha(self.db, self.conta, "1", "Campanha 1")
        self.opo = b.criar_oportunidade(self.db, self.emp.empId)

    def test_define_e_marca_manual(self) -> None:
        r = ind.definir_campanha_oportunidade(self.db, self.emp.empId, self.opo.opoId, self.camp.mcgId)
        self.assertEqual((r.opoMcgId, r.opoMcgManual), (self.camp.mcgId, True))

    def test_nenhuma_tambem_e_manual(self) -> None:
        r = ind.definir_campanha_oportunidade(self.db, self.emp.empId, self.opo.opoId, None)
        self.assertEqual((r.opoMcgId, r.opoMcgManual), (None, True))

    def test_campanha_de_outra_empresa(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        conta_outra = b.criar_conta(self.db, outra.empId)
        camp_outra = b.criar_campanha(self.db, conta_outra, "9", "X")
        with self.assertRaises(BadRequestError):
            ind.definir_campanha_oportunidade(self.db, self.emp.empId, self.opo.opoId, camp_outra.mcgId)

    def test_oportunidade_de_outra_empresa(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        with self.assertRaises(NotFoundError):
            ind.definir_campanha_oportunidade(self.db, outra.empId, self.opo.opoId, None)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run test to verify it fails**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_indicadores -v`
Expected: FAIL com `ImportError: cannot import name 'indicadores'`.

- [ ] **Step 5: Implementar** — `backend/services/meta_ads/indicadores.py`

```python
"""
Indicadores das campanhas: investimento do Meta cruzado com os leads do CRM.

Um lead "e do Meta" quando esta ligado a uma campanha (opoMcgId) ou, sem campanha, quando
sua origem esta mapeada numa conta ativa. Leads, vendas, MRR e Projeto usam as MESMAS
condicoes de periodo da aba Fontes do Dashboard (condicoes_periodo), para os numeros baterem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, case, false, func, or_, select
from sqlalchemy.orm import Session

from ...exceptions import BadRequestError, NotFoundError
from ...models.meta_ads_campanha import MetaAdsCampanha
from ...models.meta_ads_conta import MetaAdsConta
from ...models.meta_ads_conta_origem import MetaAdsContaOrigem
from ...models.meta_ads_insight_diario import MetaAdsInsightDiario
from ...models.oportunidade import Oportunidade
from ...schemas.meta_ads import (
    MetaAdsCampanhaDetalheResponse,
    MetaAdsCampanhaOpcao,
    MetaAdsCampanhaOpcoesResponse,
    MetaAdsContaOpcao,
    MetaAdsContaOpcoesResponse,
    MetaAdsLeadItem,
    MetaAdsLinha,
    MetaAdsPainelResponse,
    MetaAdsResumoResponse,
    MetaAdsSerieDia,
    OportunidadeCampanhaMetaResponse,
)
# Helpers "privados" do dashboard reusados de proposito: e a garantia de que as regras
# de MRR/Projeto e de periodo sao exatamente as mesmas da aba Fontes.
from ..crm_dashboard_service import (
    _between_dates,
    _mrr_incremental_expr,
    _valor_projeto_expr,
    condicoes_periodo,
)

NOME_NAO_IDENTIFICADA = "Meta — campanha não identificada"
GASTO_ZERO = {"investimento": 0.0, "impressoes": 0, "cliques": 0, "leadsMeta": 0}
LEADS_ZERO = {"leadsCrm": 0, "vendas": 0, "mrr": 0.0, "projeto": 0.0}


@dataclass(frozen=True)
class FiltroPainel:
    data_inicial: date | None
    data_final: date | None
    mac_id: int | None = None
    somente_ativas: bool = False


def _dividir(a: float, b: float) -> float | None:
    return round(a / b, 2) if b else None


def calcular_derivados(
    *, investimento: float, leads: int, vendas: int, mrr: float, projeto: float, impressoes: int, cliques: int
) -> dict:
    return {
        "ctr": round(cliques / impressoes * 100, 2) if impressoes else None,
        "cpc": _dividir(investimento, cliques),
        "cpl": _dividir(investimento, leads),
        "cac": _dividir(investimento, vendas),
        "retorno": _dividir(mrr * 12 + projeto, investimento),
    }


def _linha(mcg_id, nome, status, mac_id, gasto: dict, leads: dict) -> MetaAdsLinha:
    investimento = round(gasto["investimento"], 2)
    return MetaAdsLinha(
        mcgId=mcg_id,
        nome=nome,
        status=status,
        macId=mac_id,
        investimento=investimento,
        impressoes=gasto["impressoes"],
        cliques=gasto["cliques"],
        leadsMeta=gasto["leadsMeta"],
        leadsCrm=leads["leadsCrm"],
        vendas=leads["vendas"],
        mrr=round(leads["mrr"], 2),
        projeto=round(leads["projeto"], 2),
        **calcular_derivados(
            investimento=investimento,
            leads=leads["leadsCrm"],
            vendas=leads["vendas"],
            mrr=leads["mrr"],
            projeto=leads["projeto"],
            impressoes=gasto["impressoes"],
            cliques=gasto["cliques"],
        ),
    )


def _tem_movimento(gasto: dict, leads: dict) -> bool:
    return bool(
        gasto["investimento"] or gasto["leadsMeta"] or leads["leadsCrm"] or leads["vendas"] or leads["mrr"] or leads["projeto"]
    )


def tem_conta(db: Session, emp_id: int) -> bool:
    return (
        db.execute(
            select(MetaAdsConta.macId)
            .where(MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True))
            .limit(1)
        ).first()
        is not None
    )


def _origens_meta(db: Session, emp_id: int, mac_id: int | None) -> list[int]:
    stmt = (
        select(MetaAdsContaOrigem.mcoCcoId)
        .join(MetaAdsConta, MetaAdsConta.macId == MetaAdsContaOrigem.mcoMacId)
        .where(MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True))
    )
    if mac_id is not None:
        stmt = stmt.where(MetaAdsConta.macId == mac_id)
    return sorted(set(db.execute(stmt).scalars()))


def _condicao_lead_meta(db: Session, emp_id: int, mac_id: int | None):
    if mac_id is None:
        ligada = Oportunidade.opoMcgId.isnot(None)
    else:
        ligada = Oportunidade.opoMcgId.in_(
            select(MetaAdsCampanha.mcgId).where(MetaAdsCampanha.mcgMacId == mac_id)
        )
    origens = _origens_meta(db, emp_id, mac_id)
    sem_campanha = (
        and_(Oportunidade.opoMcgId.is_(None), Oportunidade.opoCcoId.in_(origens))
        if origens
        else false()
    )
    return or_(ligada, sem_campanha)


def _gastos(db: Session, emp_id: int, filtro: FiltroPainel) -> dict[int, dict]:
    m = MetaAdsInsightDiario
    conds = [m.midEmpId == emp_id]
    periodo = _between_dates(m.midData, filtro.data_inicial, filtro.data_final)
    if periodo is not None:
        conds.append(periodo)
    if filtro.mac_id is not None:
        conds.append(m.midMacId == filtro.mac_id)
    stmt = (
        select(
            m.midMcgId,
            func.coalesce(func.sum(m.midInvestimento), 0).label("inv"),
            func.coalesce(func.sum(m.midImpressoes), 0).label("imp"),
            func.coalesce(func.sum(m.midCliques), 0).label("cli"),
            func.coalesce(func.sum(m.midLeadsMeta), 0).label("lm"),
        )
        .where(*conds)
        .group_by(m.midMcgId)
    )
    return {
        r.midMcgId: {
            "investimento": float(r.inv),
            "impressoes": int(r.imp),
            "cliques": int(r.cli),
            "leadsMeta": int(r.lm),
        }
        for r in db.execute(stmt)
    }


def _leads(db: Session, emp_id: int, filtro: FiltroPainel) -> dict[int | None, dict]:
    cond = condicoes_periodo(filtro.data_inicial, filtro.data_final)
    stmt = (
        select(
            Oportunidade.opoMcgId,
            func.coalesce(func.sum(case((cond.recebidas, 1), else_=0)), 0).label("rec"),
            func.coalesce(func.sum(case((cond.ganhas, 1), else_=0)), 0).label("gan"),
            func.coalesce(func.sum(_mrr_incremental_expr()), 0).label("mrr"),
            func.coalesce(func.sum(_valor_projeto_expr()), 0).label("proj"),
        )
        .where(
            Oportunidade.opoEmpId == emp_id,
            _condicao_lead_meta(db, emp_id, filtro.mac_id),
            cond.escopo,
        )
        .group_by(Oportunidade.opoMcgId)
    )
    return {
        r.opoMcgId: {
            "leadsCrm": int(r.rec),
            "vendas": int(r.gan),
            "mrr": float(r.mrr),
            "projeto": float(r.proj),
        }
        for r in db.execute(stmt)
    }


def _somar(linhas: list[MetaAdsLinha]) -> MetaAdsLinha:
    gasto = {k: sum(getattr(l, k) for l in linhas) for k in GASTO_ZERO}
    leads = {k: sum(getattr(l, k) for l in linhas) for k in LEADS_ZERO}
    return _linha(None, "Total", None, None, gasto, leads)


def painel(db: Session, emp_id: int, filtro: FiltroPainel) -> MetaAdsPainelResponse:
    gastos = _gastos(db, emp_id, filtro)
    leads = _leads(db, emp_id, filtro)
    ids = {i for i in set(gastos) | set(leads) if i is not None}
    campanhas = {
        c.mcgId: c
        for c in db.execute(select(MetaAdsCampanha).where(MetaAdsCampanha.mcgId.in_(ids))).scalars()
    } if ids else {}

    linhas: list[MetaAdsLinha] = []
    for mcg_id, camp in campanhas.items():
        if camp.mcgEmpId != emp_id:
            continue
        if filtro.somente_ativas and camp.mcgStatus != "ACTIVE":
            continue
        gasto = gastos.get(mcg_id, GASTO_ZERO)
        lead = leads.get(mcg_id, LEADS_ZERO)
        if _tem_movimento(gasto, lead):
            linhas.append(_linha(mcg_id, camp.mcgNome, camp.mcgStatus, camp.mcgMacId, gasto, lead))
    linhas.sort(key=lambda l: (l.investimento, l.leadsCrm), reverse=True)

    nao_identificada = None
    if None in leads and _tem_movimento(GASTO_ZERO, leads[None]):
        nao_identificada = _linha(None, NOME_NAO_IDENTIFICADA, None, None, GASTO_ZERO, leads[None])

    total = _somar(linhas + ([nao_identificada] if nao_identificada else []))
    return MetaAdsPainelResponse(
        temConta=tem_conta(db, emp_id), total=total, campanhas=linhas, naoIdentificada=nao_identificada
    )


def _campanha_da_empresa(db: Session, emp_id: int, mcg_id: int) -> MetaAdsCampanha:
    camp = db.get(MetaAdsCampanha, mcg_id)
    if camp is None or camp.mcgEmpId != emp_id:
        raise NotFoundError("Campanha não encontrada")
    return camp


def detalhe_campanha(
    db: Session, emp_id: int, mcg_id: int, data_inicial: date | None, data_final: date | None
) -> MetaAdsCampanhaDetalheResponse:
    camp = _campanha_da_empresa(db, emp_id, mcg_id)
    filtro = FiltroPainel(data_inicial, data_final, mac_id=camp.mcgMacId)
    linha = next(
        (l for l in painel(db, emp_id, filtro).campanhas if l.mcgId == mcg_id),
        _linha(mcg_id, camp.mcgNome, camp.mcgStatus, camp.mcgMacId, GASTO_ZERO, LEADS_ZERO),
    )

    m = MetaAdsInsightDiario
    conds = [m.midMcgId == mcg_id]
    periodo = _between_dates(m.midData, data_inicial, data_final)
    if periodo is not None:
        conds.append(periodo)
    dias: dict[date, dict] = {}
    for r in db.execute(
        select(m.midData, m.midInvestimento, m.midLeadsMeta).where(*conds)
    ):
        dias[r.midData] = {"investimento": float(r.midInvestimento), "leadsMeta": r.midLeadsMeta, "leadsCrm": 0}

    cond = condicoes_periodo(data_inicial, data_final)
    for r in db.execute(
        select(Oportunidade.opoDataRecebimento, func.count(Oportunidade.opoId).label("n"))
        .where(Oportunidade.opoMcgId == mcg_id, cond.recebidas)
        .group_by(Oportunidade.opoDataRecebimento)
    ):
        dia = dias.setdefault(r.opoDataRecebimento, {"investimento": 0.0, "leadsMeta": 0, "leadsCrm": 0})
        dia["leadsCrm"] = int(r.n)
    serie = [MetaAdsSerieDia(data=d, **v) for d, v in sorted(dias.items())]

    oportunidades = db.execute(
        select(Oportunidade)
        .where(
            Oportunidade.opoMcgId == mcg_id,
            or_(cond.recebidas, cond.ganhas, cond.perdidas),
        )
        .order_by(Oportunidade.opoDataRecebimento.desc(), Oportunidade.opoId.desc())
        .limit(500)
    ).scalars()
    leads = [
        MetaAdsLeadItem(
            opoId=o.opoId,
            opoTitulo=o.opoTitulo,
            opoNomeContato=o.opoNomeContato,
            opoDataRecebimento=o.opoDataRecebimento,
            opoStatusFechamento=o.opoStatusFechamento,
            opoValorFechado=float(o.opoValorFechado) if o.opoValorFechado is not None else None,
        )
        for o in oportunidades
    ]
    return MetaAdsCampanhaDetalheResponse(campanha=linha, serie=serie, leads=leads)


def resumo(db: Session, emp_id: int, data_inicial: date | None, data_final: date | None) -> MetaAdsResumoResponse:
    p = painel(db, emp_id, FiltroPainel(data_inicial, data_final))
    t = p.total
    return MetaAdsResumoResponse(
        temConta=p.temConta,
        investimento=t.investimento,
        leadsCrm=t.leadsCrm,
        vendas=t.vendas,
        cpl=t.cpl,
        cac=t.cac,
        retorno=t.retorno,
    )


def opcoes_campanhas(db: Session, emp_id: int) -> MetaAdsCampanhaOpcoesResponse:
    linhas = db.execute(
        select(MetaAdsCampanha, MetaAdsConta.macNome)
        .join(MetaAdsConta, MetaAdsConta.macId == MetaAdsCampanha.mcgMacId)
        .where(MetaAdsCampanha.mcgEmpId == emp_id)
        .order_by(case((MetaAdsCampanha.mcgStatus == "ACTIVE", 0), else_=1), MetaAdsCampanha.mcgNome)
    ).all()
    return MetaAdsCampanhaOpcoesResponse(
        items=[
            MetaAdsCampanhaOpcao(mcgId=c.mcgId, nome=c.mcgNome, conta=nome_conta, status=c.mcgStatus)
            for c, nome_conta in linhas
        ]
    )


def opcoes_contas(db: Session, emp_id: int) -> MetaAdsContaOpcoesResponse:
    linhas = db.execute(
        select(MetaAdsConta.macId, MetaAdsConta.macNome)
        .where(MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True))
        .order_by(MetaAdsConta.macNome)
    ).all()
    return MetaAdsContaOpcoesResponse(items=[MetaAdsContaOpcao(macId=i, macNome=n) for i, n in linhas])


def definir_campanha_oportunidade(
    db: Session, emp_id: int, opo_id: int, mcg_id: int | None
) -> OportunidadeCampanhaMetaResponse:
    opo = db.get(Oportunidade, opo_id)
    if opo is None or opo.opoEmpId != emp_id or not opo.opoAtivo:
        raise NotFoundError("Oportunidade não encontrada")
    if mcg_id is not None:
        camp = db.get(MetaAdsCampanha, mcg_id)
        if camp is None or camp.mcgEmpId != emp_id:
            raise BadRequestError("Campanha inválida para esta empresa")
    opo.opoMcgId = mcg_id
    opo.opoMcgManual = True
    db.commit()
    return OportunidadeCampanhaMetaResponse(opoId=opo.opoId, opoMcgId=opo.opoMcgId, opoMcgManual=True)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/Scripts/python -m unittest backend.tests.test_meta_ads_indicadores -v`
Expected: 17 testes OK. Se `test_bate_com_a_aba_fontes` falhar, a divergência está na condição de lead Meta ou nas condições de período — **não** ajustar o teste; corrigir `_leads`.

- [ ] **Step 7: Rotas de leitura** — no fim de `backend/routers/meta_ads_router.py`

Adicionar aos imports: `from datetime import date`, `from fastapi import Query`, os schemas `MetaAdsCampanhaDetalheResponse, MetaAdsCampanhaOpcoesResponse, MetaAdsContaOpcoesResponse, MetaAdsPainelResponse, MetaAdsResumoResponse, OportunidadeCampanhaMetaRequest, OportunidadeCampanhaMetaResponse`, e `indicadores` em `from ..services.meta_ads import contas, indicadores, sincronizacao`.

```python
@router.get("/painel", response_model=MetaAdsPainelResponse)
def painel(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    data_inicial: date | None = Query(default=None),
    data_final: date | None = Query(default=None),
    mac_id: int | None = Query(default=None, alias="macId"),
    somente_ativas: bool = Query(default=False),
) -> MetaAdsPainelResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    return indicadores.painel(
        db, emp_id, indicadores.FiltroPainel(data_inicial, data_final, mac_id, somente_ativas)
    )


@router.get("/campanhas-opcoes", response_model=MetaAdsCampanhaOpcoesResponse)
def campanhas_opcoes(
    db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsCampanhaOpcoesResponse:
    return indicadores.opcoes_campanhas(db, empresa_obrigatoria(db, current_user, company_id))


@router.get("/contas-opcoes", response_model=MetaAdsContaOpcoesResponse)
def contas_opcoes(
    db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsContaOpcoesResponse:
    return indicadores.opcoes_contas(db, empresa_obrigatoria(db, current_user, company_id))


@router.get("/campanhas/{mcg_id}", response_model=MetaAdsCampanhaDetalheResponse)
def detalhe_campanha(
    mcg_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    data_inicial: date | None = Query(default=None),
    data_final: date | None = Query(default=None),
) -> MetaAdsCampanhaDetalheResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    return indicadores.detalhe_campanha(db, emp_id, mcg_id, data_inicial, data_final)


@router.get("/resumo", response_model=MetaAdsResumoResponse)
def resumo(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    data_inicial: date | None = Query(default=None),
    data_final: date | None = Query(default=None),
) -> MetaAdsResumoResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    return indicadores.resumo(db, emp_id, data_inicial, data_final)


@router.patch("/oportunidades/{opo_id}/campanha", response_model=OportunidadeCampanhaMetaResponse)
def definir_campanha(
    opo_id: int,
    data: OportunidadeCampanhaMetaRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeCampanhaMetaResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    return indicadores.definir_campanha_oportunidade(db, emp_id, opo_id, data.opoMcgId)
```

Adicionar em `backend/tests/test_meta_ads_router.py`, na classe `RotasTests`:

```python
    def test_leitura_liberada_para_nao_admin(self) -> None:
        self.usuario.usuAdmin = False
        with patch.object(meta_ads_router, "require_user_in_company"):
            r = self.http.get("/api/meta-ads/painel", headers=self.h, params={"data_inicial": "2026-10-01"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertFalse(r.json()["temConta"])
```

- [ ] **Step 8: Rodar a suíte inteira**

Run: `.venv/Scripts/python -m unittest $(ls backend/tests/test_*.py | sed 's#/#.#g; s#\.py$##' | tr '\n' ' ')`
Expected: todos OK.

- [ ] **Step 9: Commit**

```bash
git add backend/services/crm_dashboard_service.py backend/services/meta_ads/indicadores.py backend/schemas/meta_ads.py backend/routers/meta_ads_router.py backend/tests/test_meta_ads_indicadores.py backend/tests/test_meta_ads_router.py
git commit -m "Meta Ads: indicadores por campanha, resumo e vínculo manual

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Tela de configuração das contas (Integrações → Meta Ads)

**Files:**
- Create: `frontend/src/pages/Campanhas/metaAdsTipos.ts`, `frontend/src/pages/Integracoes/MetaAdsContasPage.tsx`
- Modify: `frontend/src/App.tsx` (import + rota `/integracoes/meta-ads`), `frontend/src/components/Layout.tsx` (item "Meta Ads" no grupo Integrações, depois de "Webhooks")

**Interfaces:**
- Consumes: rotas admin da Task 7; `GET /como-conheceu`.
- Produces: em `metaAdsTipos.ts` — tipos `MetaAdsLinha`, `MetaAdsPainel`, `MetaAdsSerieDia`, `MetaAdsLeadItem`, `MetaAdsCampanhaDetalhe`, `MetaAdsResumo`, `MetaAdsContaOpcao`; formatadores `moeda(v)`, `inteiro(v)`, `percentual(v)`, `multiplicador(v)`, `dataBR(v)`; `rotuloStatusCampanha(s)`; `intervaloAnoCorrente()`.

- [ ] **Step 1: Tipos e formatadores** — `frontend/src/pages/Campanhas/metaAdsTipos.ts`

```ts
export interface MetaAdsLinha {
  mcgId: number | null;
  nome: string;
  status: string | null;
  macId: number | null;
  investimento: number;
  impressoes: number;
  cliques: number;
  leadsMeta: number;
  leadsCrm: number;
  vendas: number;
  mrr: number;
  projeto: number;
  ctr: number | null;
  cpc: number | null;
  cpl: number | null;
  cac: number | null;
  retorno: number | null;
}

export interface MetaAdsPainel {
  temConta: boolean;
  total: MetaAdsLinha;
  campanhas: MetaAdsLinha[];
  naoIdentificada: MetaAdsLinha | null;
}

export interface MetaAdsSerieDia {
  data: string;
  investimento: number;
  leadsMeta: number;
  leadsCrm: number;
}

export interface MetaAdsLeadItem {
  opoId: number;
  opoTitulo: string;
  opoNomeContato: string | null;
  opoDataRecebimento: string | null;
  opoStatusFechamento: string | null;
  opoValorFechado: number | null;
}

export interface MetaAdsCampanhaDetalhe {
  campanha: MetaAdsLinha;
  serie: MetaAdsSerieDia[];
  leads: MetaAdsLeadItem[];
}

export interface MetaAdsResumo {
  temConta: boolean;
  investimento: number;
  leadsCrm: number;
  vendas: number;
  cpl: number | null;
  cac: number | null;
  retorno: number | null;
}

export interface MetaAdsContaOpcao {
  macId: number;
  macNome: string;
}

export const moeda = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 });

export const inteiro = (v: number) => v.toLocaleString("pt-BR");

export const percentual = (v: number | null) =>
  v == null ? "—" : `${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;

export const multiplicador = (v: number | null) =>
  v == null ? "—" : `${v.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}×`;

export const dataBR = (v: string | null) => {
  if (!v) return "—";
  const [a, m, d] = v.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
};

const STATUS_CAMPANHA: Record<string, string> = {
  ACTIVE: "Ativa",
  PAUSED: "Pausada",
  CAMPAIGN_PAUSED: "Pausada",
  ARCHIVED: "Arquivada",
  DELETED: "Excluída",
  IN_PROCESS: "Em análise",
  WITH_ISSUES: "Com problemas",
};

export const rotuloStatusCampanha = (s: string | null) => (s ? STATUS_CAMPANHA[s] ?? s : "—");

const isoLocal = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export function intervaloAnoCorrente(): { inicio: string; fim: string } {
  const hoje = new Date();
  return { inicio: `${hoje.getFullYear()}-01-01`, fim: isoLocal(hoje) };
}

export function intervaloMesCorrente(): { inicio: string; fim: string } {
  const hoje = new Date();
  return { inicio: isoLocal(new Date(hoje.getFullYear(), hoje.getMonth(), 1)), fim: isoLocal(hoje) };
}
```

- [ ] **Step 2: Página** — `frontend/src/pages/Integracoes/MetaAdsContasPage.tsx`

```tsx
import React, { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import ListingTableCard from "../../components/ListingTableCard";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import { useAuth } from "../../contexts/AuthContext";

interface Conta {
  macId: number;
  macNome: string;
  macContaExterna: string;
  macTokenFinal: string;
  macMoeda: string | null;
  macFuso: string | null;
  macStatus: string;
  macMensagem: string | null;
  macUltimaSync: string | null;
  macCargaInicialFeita: boolean;
  macAtivo: boolean;
  origens: number[];
}

interface Origem {
  ccoId: number;
  ccoNome: string;
}

interface SyncLog {
  mslId: number;
  mslInicio: string;
  mslFim: string;
  mslOrigem: string;
  mslStatus: string;
  mslLinhas: number;
  mslLeadsVinculados: number;
  mslErro: string | null;
  mslDuracaoMs: number | null;
  mslDataExecucao: string;
}

const dataHora = (valor: string | null) => (valor ? new Date(valor).toLocaleString("pt-BR") : "—");

const STATUS: Record<string, { rotulo: string; classe: string }> = {
  pendente: { rotulo: "Aguardando sincronização", classe: "integracao-badge--warn" },
  sincronizando: { rotulo: "Sincronizando…", classe: "integracao-badge--warn" },
  ok: { rotulo: "OK", classe: "integracao-badge--ok" },
  aviso: { rotulo: "Aviso", classe: "integracao-badge--warn" },
  erro: { rotulo: "Erro", classe: "integracao-badge--danger" },
  token_invalido: { rotulo: "Token inválido", classe: "integracao-badge--danger" },
};

const badge = (status: string) => {
  const s = STATUS[status] ?? { rotulo: status, classe: "integracao-badge--warn" };
  return <span className={`integracao-badge ${s.classe}`}>{s.rotulo}</span>;
};

const FORM_VAZIO = { nome: "", conta: "", token: "", origens: [] as number[] };

const MetaAdsContasPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<Conta[]>([]);
  const [origens, setOrigens] = useState<Origem[]>([]);
  const [loading, setLoading] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Conta | null>(null);
  const [form, setForm] = useState(FORM_VAZIO);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [logsDe, setLogsDe] = useState<Conta | null>(null);
  const [logs, setLogs] = useState<SyncLog[]>([]);
  const [periodoOpen, setPeriodoOpen] = useState(false);
  const [periodo, setPeriodo] = useState({ inicio: "", fim: "", macId: "" });

  const avisar = (texto: string) => {
    setAviso(texto);
    setTimeout(() => setAviso(null), 7000);
  };

  const mensagemErro = (err: any, padrao: string) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg).replace(/^Value error, /, "");
    return padrao;
  };

  const carregar = async () => {
    setLoading(true);
    try {
      const [lista, cco] = await Promise.all([
        api.get<{ items: Conta[] }>("/meta-ads/contas"),
        api.get<{ items: Origem[] }>("/como-conheceu", { params: { status: "ativos", page_size: 100 } }),
      ]);
      setItems(lista.data.items ?? []);
      setOrigens((cco.data.items ?? []).sort((a, b) => a.ccoNome.localeCompare(b.ccoNome)));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrirNovo = () => {
    setEditando(null);
    setForm(FORM_VAZIO);
    setErro(null);
    setModalOpen(true);
  };

  const abrirEdicao = (row: Conta) => {
    setEditando(row);
    setForm({ nome: row.macNome, conta: row.macContaExterna, token: "", origens: row.origens });
    setErro(null);
    setModalOpen(true);
  };

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    setErro(null);
    try {
      if (editando) {
        const corpo: Record<string, unknown> = { macNome: form.nome, origens: form.origens };
        if (form.token.trim()) corpo.token = form.token;
        await api.put(`/meta-ads/contas/${editando.macId}`, corpo);
      } else {
        await api.post("/meta-ads/contas", {
          macNome: form.nome,
          macContaExterna: form.conta,
          token: form.token,
          origens: form.origens,
        });
      }
      setModalOpen(false);
      await carregar();
    } catch (err: any) {
      setErro(mensagemErro(err, "Não foi possível salvar a conta."));
    } finally {
      setSalvando(false);
    }
  };

  const testar = async (row: Conta) => {
    const res = await api.post<{ ok: boolean; nome: string | null; moeda: string | null; fuso: string | null; mensagem: string | null }>(
      `/meta-ads/contas/${row.macId}/testar`
    );
    if (res.data.ok) {
      avisar(`Conexão OK: "${res.data.nome}" (${res.data.moeda ?? "?"}, ${res.data.fuso ?? "?"}).`);
    } else {
      avisar(`Falha na conexão: ${res.data.mensagem}`);
    }
    await carregar();
  };

  const sincronizar = async (row: Conta) => {
    try {
      await api.post(`/meta-ads/contas/${row.macId}/sincronizar`);
      avisar(`Sincronização de "${row.macNome}" iniciada. Atualize a página em alguns instantes.`);
    } catch (err: any) {
      avisar(mensagemErro(err, "Não foi possível iniciar a sincronização."));
    }
    await carregar();
  };

  const reprocessar = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/meta-ads/sincronizar-periodo", {
        data_inicial: periodo.inicio,
        data_final: periodo.fim,
        macId: periodo.macId ? Number(periodo.macId) : null,
      });
      setPeriodoOpen(false);
      avisar("Reprocessamento iniciado.");
      await carregar();
    } catch (err: any) {
      avisar(mensagemErro(err, "Não foi possível reprocessar o período."));
    }
  };

  const alternarAtivo = async (row: Conta) => {
    await api.put(`/meta-ads/contas/${row.macId}`, { macAtivo: !row.macAtivo });
    await carregar();
  };

  const verLogs = async (row: Conta) => {
    setLogsDe(row);
    const res = await api.get<{ items: SyncLog[] }>(`/meta-ads/contas/${row.macId}/logs`);
    setLogs(res.data.items ?? []);
  };

  const alternarOrigem = (id: number) =>
    setForm((f) => ({
      ...f,
      origens: f.origens.includes(id) ? f.origens.filter((o) => o !== id) : [...f.origens, id],
    }));

  const nomeOrigem = (id: number) => origens.find((o) => o.ccoId === id)?.ccoNome ?? `#${id}`;

  return (
    <Layout>
      <section className="surface-card details-card integracao-header">
        <div>
          <h2 className="section-title">Meta Ads</h2>
          <p className="muted-text">
            Conecte as contas de anúncio da empresa para ver investimento, custo por lead e retorno por campanha.
            A sincronização roda todo dia de madrugada e regrava os últimos 30 dias.
          </p>
        </div>
        <div className="integracao-acoes">
          <button type="button" onClick={() => setPeriodoOpen(true)} disabled={items.length === 0}>
            Reprocessar período
          </button>
          <button type="button" className="primary" onClick={abrirNovo}>
            Conectar conta
          </button>
        </div>
      </section>

      {aviso ? (
        <div className="integracao-aviso" role="status">
          {aviso}
        </div>
      ) : null}

      <ListingTableCard>
        {loading ? (
          <Loader />
        ) : items.length === 0 ? (
          <div className="datatable-empty">Nenhuma conta conectada. Veja docs/META_ADS.md para gerar o token.</div>
        ) : (
          <table className="datatable">
            <thead>
              <tr>
                <th>Conta</th>
                <th>Token</th>
                <th>Origens Meta</th>
                <th>Última sincronização</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.macId}>
                  <td>
                    <strong>{row.macNome}</strong>
                    <div className="muted-text integracao-subtexto">
                      {row.macContaExterna}
                      {row.macMoeda ? ` · ${row.macMoeda}` : ""}
                    </div>
                  </td>
                  <td>
                    <code>••••{row.macTokenFinal}</code>
                  </td>
                  <td>
                    {row.origens.length === 0
                      ? "—"
                      : row.origens.map((id) => (
                          <code key={id} className="integracao-escopo">
                            {nomeOrigem(id)}
                          </code>
                        ))}
                  </td>
                  <td>{dataHora(row.macUltimaSync)}</td>
                  <td>
                    {row.macAtivo ? badge(row.macStatus) : <span className="integracao-badge integracao-badge--danger">Desativada</span>}
                    {row.macMensagem ? <div className="muted-text integracao-subtexto">{row.macMensagem}</div> : null}
                  </td>
                  <td className="integracao-acoes">
                    <button type="button" onClick={() => abrirEdicao(row)}>
                      Editar
                    </button>
                    <button type="button" onClick={() => void testar(row)}>
                      Testar conexão
                    </button>
                    <button type="button" onClick={() => void sincronizar(row)} disabled={!row.macAtivo}>
                      Sincronizar agora
                    </button>
                    <button type="button" onClick={() => void verLogs(row)}>
                      Log
                    </button>
                    <button type="button" onClick={() => void alternarAtivo(row)}>
                      {row.macAtivo ? "Desativar" : "Reativar"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ListingTableCard>

      <Modal
        isOpen={modalOpen}
        title={editando ? `Editar: ${editando.macNome}` : "Conectar conta de anúncios"}
        onClose={() => !salvando && setModalOpen(false)}
      >
        <form onSubmit={(e) => void salvar(e)}>
          {erro ? (
            <div className="integracao-erro" role="alert">
              {erro}
            </div>
          ) : null}
          <label>
            Nome
            <input
              value={form.nome}
              onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
              placeholder="Ex.: Conta principal"
              required
              disabled={salvando}
            />
          </label>
          <label>
            ID da conta de anúncios
            <input
              value={form.conta}
              onChange={(e) => setForm((f) => ({ ...f, conta: e.target.value }))}
              placeholder="act_1234567890"
              required
              disabled={salvando || Boolean(editando)}
            />
          </label>
          <label>
            Token do System User
            <input
              type="password"
              autoComplete="off"
              value={form.token}
              onChange={(e) => setForm((f) => ({ ...f, token: e.target.value }))}
              placeholder={editando ? `Deixe vazio para manter ••••${editando.macTokenFinal}` : "EAAB…"}
              required={!editando}
              disabled={salvando}
            />
            <span className="field-hint">Precisa da permissão ads_read na conta. O token fica criptografado e não é exibido de novo.</span>
          </label>
          <fieldset className="integracao-escopos">
            <legend>Origens que contam como Meta Ads</legend>
            {origens.map((o) => (
              <label key={o.ccoId} className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={form.origens.includes(o.ccoId)}
                  onChange={() => alternarOrigem(o.ccoId)}
                  disabled={salvando}
                />
                {o.ccoNome}
              </label>
            ))}
            <span className="field-hint">
              Leads dessas origens sem campanha identificada entram no total da conta, como "campanha não identificada".
            </span>
          </fieldset>
          <div className="modal-actions">
            <button type="button" onClick={() => setModalOpen(false)} disabled={salvando}>
              Cancelar
            </button>
            <button type="submit" className="primary" disabled={salvando || !form.nome.trim()}>
              {salvando ? "Salvando…" : "Salvar"}
            </button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={periodoOpen} title="Reprocessar período" onClose={() => setPeriodoOpen(false)}>
        <form onSubmit={(e) => void reprocessar(e)}>
          <label>
            De
            <input type="date" value={periodo.inicio} onChange={(e) => setPeriodo((p) => ({ ...p, inicio: e.target.value }))} required />
          </label>
          <label>
            Até
            <input type="date" value={periodo.fim} onChange={(e) => setPeriodo((p) => ({ ...p, fim: e.target.value }))} required />
          </label>
          <label>
            Conta
            <select value={periodo.macId} onChange={(e) => setPeriodo((p) => ({ ...p, macId: e.target.value }))}>
              <option value="">Todas as contas ativas</option>
              {items.filter((c) => c.macAtivo).map((c) => (
                <option key={c.macId} value={c.macId}>
                  {c.macNome}
                </option>
              ))}
            </select>
            <span className="field-hint">Máximo de 366 dias.</span>
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setPeriodoOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="primary">
              Reprocessar
            </button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={Boolean(logsDe)} title={`Log: ${logsDe?.macNome ?? ""}`} onClose={() => setLogsDe(null)}>
        {logs.length === 0 ? (
          <p className="muted-text">Nenhuma sincronização registrada ainda.</p>
        ) : (
          <table className="datatable">
            <thead>
              <tr>
                <th>Quando</th>
                <th>Período</th>
                <th>Origem</th>
                <th>Status</th>
                <th>Linhas</th>
                <th>Leads ligados</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.mslId}>
                  <td>{dataHora(l.mslDataExecucao)}</td>
                  <td>
                    {l.mslInicio} → {l.mslFim}
                  </td>
                  <td>{l.mslOrigem}</td>
                  <td>
                    {badge(l.mslStatus)}
                    {l.mslErro ? <div className="muted-text integracao-subtexto">{l.mslErro}</div> : null}
                  </td>
                  <td>{l.mslLinhas}</td>
                  <td>{l.mslLeadsVinculados}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Modal>
    </Layout>
  );
};

export default MetaAdsContasPage;
```

- [ ] **Step 3: Rota e menu**

Em `frontend/src/App.tsx`: `import MetaAdsContasPage from "./pages/Integracoes/MetaAdsContasPage";` junto dos imports de Integrações e, depois da rota `/integracoes/webhooks`:

```tsx
      <Route
        path="/integracoes/meta-ads"
        element={
          <ProtectedRoute>
            <MetaAdsContasPage />
          </ProtectedRoute>
        }
      />
```

Em `frontend/src/components/Layout.tsx`, depois do `NavLink` de `/integracoes/webhooks`:

```tsx
                  <NavLink to="/integracoes/meta-ads" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                    Meta Ads
                  </NavLink>
```

- [ ] **Step 4: Verificar tipos e build**

Run (em `frontend/`): `npx tsc --noEmit -p . 2>&1 | grep -c "error TS"`
Expected: `6` (os mesmos pré-existentes).
Run: `npm run build`
Expected: build sem erro.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Campanhas/metaAdsTipos.ts frontend/src/pages/Integracoes/MetaAdsContasPage.tsx frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "Meta Ads: tela de contas em Integrações

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Página Campanhas

**Files:**
- Create: `frontend/src/pages/Campanhas/CampanhasPage.tsx`, `frontend/src/pages/Campanhas/CampanhaDetalheModal.tsx`
- Modify: `frontend/src/App.tsx` (rota `/campanhas`), `frontend/src/components/Layout.tsx` (item "Campanhas" no grupo CRM, depois de "Kanban"), `frontend/src/styles.css` (bloco novo no fim)

**Interfaces:**
- Consumes: `GET /meta-ads/painel`, `GET /meta-ads/contas-opcoes`, `GET /meta-ads/campanhas/{id}` (Task 8); tipos e formatadores da Task 9.

- [ ] **Step 1: Modal de detalhe** — `frontend/src/pages/Campanhas/CampanhaDetalheModal.tsx`

```tsx
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import { useAuth } from "../../contexts/AuthContext";
import {
  MetaAdsCampanhaDetalhe,
  MetaAdsSerieDia,
  dataBR,
  moeda,
  multiplicador,
} from "./metaAdsTipos";

const GraficoDiario: React.FC<{ serie: MetaAdsSerieDia[] }> = ({ serie }) => {
  if (serie.length === 0) return <p className="muted-text">Sem movimento no período.</p>;
  const largura = 640;
  const altura = 180;
  const passo = largura / serie.length;
  const maxInv = Math.max(1, ...serie.map((d) => d.investimento));
  const maxLeads = Math.max(1, ...serie.map((d) => d.leadsCrm));
  const pontos = serie
    .map((d, i) => `${i * passo + passo / 2},${altura - (d.leadsCrm / maxLeads) * (altura - 10)}`)
    .join(" ");
  return (
    <div className="campanha-grafico">
      <svg viewBox={`0 0 ${largura} ${altura}`} role="img" aria-label="Investimento e leads por dia">
        {serie.map((d, i) => {
          const h = (d.investimento / maxInv) * (altura - 10);
          return (
            <rect key={d.data} x={i * passo + passo * 0.15} y={altura - h} width={passo * 0.7} height={h} className="campanha-grafico-barra">
              <title>{`${dataBR(d.data)}: ${moeda(d.investimento)} · ${d.leadsCrm} lead(s) no CRM · ${d.leadsMeta} no Meta`}</title>
            </rect>
          );
        })}
        <polyline points={pontos} className="campanha-grafico-linha" />
      </svg>
      <div className="campanha-grafico-legenda muted-text">
        <span className="campanha-legenda-barra" /> Investimento <span className="campanha-legenda-linha" /> Leads no CRM
      </div>
    </div>
  );
};

const CampanhaDetalheModal: React.FC<{
  mcgId: number | null;
  inicio: string;
  fim: string;
  onClose: () => void;
}> = ({ mcgId, inicio, fim, onClose }) => {
  const { api } = useAuth();
  const [dados, setDados] = useState<MetaAdsCampanhaDetalhe | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (mcgId == null) return;
    setLoading(true);
    setDados(null);
    api
      .get<MetaAdsCampanhaDetalhe>(`/meta-ads/campanhas/${mcgId}`, { params: { data_inicial: inicio || undefined, data_final: fim || undefined } })
      .then((res) => setDados(res.data))
      .finally(() => setLoading(false));
  }, [api, mcgId, inicio, fim]);

  const c = dados?.campanha;
  return (
    <Modal isOpen={mcgId != null} title={c?.nome ?? "Campanha"} onClose={onClose}>
      {loading || !dados || !c ? (
        <Loader />
      ) : (
        <div className="campanha-detalhe">
          <div className="campanha-detalhe-kpis">
            <span>Investimento <strong>{moeda(c.investimento)}</strong></span>
            <span>Leads CRM <strong>{c.leadsCrm}</strong></span>
            <span>CPL <strong>{moeda(c.cpl)}</strong></span>
            <span>Vendas <strong>{c.vendas}</strong></span>
            <span>CAC <strong>{moeda(c.cac)}</strong></span>
            <span>Retorno <strong>{multiplicador(c.retorno)}</strong></span>
          </div>
          <GraficoDiario serie={dados.serie} />
          <h3 className="detail-field-group-title">Leads da campanha</h3>
          {dados.leads.length === 0 ? (
            <p className="muted-text">Nenhum lead ligado a esta campanha no período.</p>
          ) : (
            <table className="datatable">
              <thead>
                <tr>
                  <th>Oportunidade</th>
                  <th>Contato</th>
                  <th>Recebida</th>
                  <th>Status</th>
                  <th>Valor fechado</th>
                </tr>
              </thead>
              <tbody>
                {dados.leads.map((l) => (
                  <tr key={l.opoId}>
                    <td>
                      <Link to={`/oportunidades/${l.opoId}`}>{l.opoTitulo}</Link>
                    </td>
                    <td>{l.opoNomeContato ?? "—"}</td>
                    <td>{dataBR(l.opoDataRecebimento)}</td>
                    <td>{l.opoStatusFechamento ?? "Em aberto"}</td>
                    <td>{l.opoValorFechado != null ? moeda(l.opoValorFechado) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </Modal>
  );
};

export default CampanhaDetalheModal;
```

Antes de salvar, conferir em `App.tsx` qual é o caminho da rota de detalhe da oportunidade (`/oportunidades/:id`) e ajustar o `Link` se for outro.

- [ ] **Step 2: Página** — `frontend/src/pages/Campanhas/CampanhasPage.tsx`

```tsx
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import { useAuth } from "../../contexts/AuthContext";
import CampanhaDetalheModal from "./CampanhaDetalheModal";
import {
  MetaAdsContaOpcao,
  MetaAdsLinha,
  MetaAdsPainel,
  intervaloAnoCorrente,
  intervaloMesCorrente,
  inteiro,
  moeda,
  multiplicador,
  percentual,
  rotuloStatusCampanha,
} from "./metaAdsTipos";

const CampanhasPage: React.FC = () => {
  const { api, user } = useAuth();
  const padrao = intervaloAnoCorrente();
  const [inicioDraft, setInicioDraft] = useState(padrao.inicio);
  const [fimDraft, setFimDraft] = useState(padrao.fim);
  const [inicio, setInicio] = useState(padrao.inicio);
  const [fim, setFim] = useState(padrao.fim);
  const [macId, setMacId] = useState<string>("");
  const [somenteAtivas, setSomenteAtivas] = useState(false);
  const [contas, setContas] = useState<MetaAdsContaOpcao[]>([]);
  const [painel, setPainel] = useState<MetaAdsPainel | null>(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [detalheId, setDetalheId] = useState<number | null>(null);

  useEffect(() => {
    api.get<{ items: MetaAdsContaOpcao[] }>("/meta-ads/contas-opcoes").then((r) => setContas(r.data.items ?? []));
  }, [api]);

  useEffect(() => {
    setLoading(true);
    setErro(null);
    api
      .get<MetaAdsPainel>("/meta-ads/painel", {
        params: {
          data_inicial: inicio || undefined,
          data_final: fim || undefined,
          macId: macId || undefined,
          somente_ativas: somenteAtivas,
        },
      })
      .then((r) => setPainel(r.data))
      .catch(() => setErro("Não foi possível carregar as campanhas."))
      .finally(() => setLoading(false));
  }, [api, inicio, fim, macId, somenteAtivas]);

  const aplicar = () => {
    setInicio(inicioDraft);
    setFim(fimDraft);
  };

  const rapido = (tipo: "mes" | "ano") => {
    const r = tipo === "mes" ? intervaloMesCorrente() : intervaloAnoCorrente();
    setInicioDraft(r.inicio);
    setFimDraft(r.fim);
    setInicio(r.inicio);
    setFim(r.fim);
  };

  const linhaTabela = (l: MetaAdsLinha, opcoes: { clicavel: boolean; classe?: string }) => (
    <tr
      key={l.mcgId ?? l.nome}
      className={`${opcoes.clicavel ? "dashboard-ranking-row--clickable" : ""} ${opcoes.classe ?? ""}`}
      tabIndex={opcoes.clicavel ? 0 : undefined}
      onClick={opcoes.clicavel ? () => setDetalheId(l.mcgId) : undefined}
      onKeyDown={
        opcoes.clicavel
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setDetalheId(l.mcgId);
              }
            }
          : undefined
      }
    >
      <td className="campanhas-col-nome">{l.nome}</td>
      <td>{l.mcgId != null ? rotuloStatusCampanha(l.status) : ""}</td>
      <td>{moeda(l.investimento)}</td>
      <td>{inteiro(l.impressoes)}</td>
      <td>{inteiro(l.cliques)}</td>
      <td>{percentual(l.ctr)}</td>
      <td>{moeda(l.cpc)}</td>
      <td>{l.leadsMeta}</td>
      <td>{l.leadsCrm}</td>
      <td>{moeda(l.cpl)}</td>
      <td>{l.vendas}</td>
      <td>{moeda(l.cac)}</td>
      <td>{moeda(l.mrr)}</td>
      <td>{moeda(l.projeto)}</td>
      <td>{multiplicador(l.retorno)}</td>
    </tr>
  );

  const semConta = painel && !painel.temConta;
  const t = painel?.total;

  return (
    <Layout>
      <section className="surface-card details-card integracao-header">
        <div>
          <h2 className="section-title">Campanhas</h2>
          <p className="muted-text">Investimento do Meta Ads cruzado com os leads e as vendas do CRM.</p>
        </div>
      </section>

      <section className="dashboard-filters campanhas-filtros">
        <label>
          De
          <input type="date" value={inicioDraft} onChange={(e) => setInicioDraft(e.target.value)} />
        </label>
        <label>
          Até
          <input type="date" value={fimDraft} onChange={(e) => setFimDraft(e.target.value)} />
        </label>
        <button type="button" className="primary" onClick={aplicar}>
          Aplicar
        </button>
        <button type="button" onClick={() => rapido("mes")}>
          Mês atual
        </button>
        <button type="button" onClick={() => rapido("ano")}>
          Ano atual
        </button>
        <label>
          Conta
          <select value={macId} onChange={(e) => setMacId(e.target.value)}>
            <option value="">Todas</option>
            {contas.map((c) => (
              <option key={c.macId} value={c.macId}>
                {c.macNome}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox-inline">
          <input type="checkbox" checked={somenteAtivas} onChange={(e) => setSomenteAtivas(e.target.checked)} />
          Só campanhas ativas
        </label>
      </section>

      {loading && <Loader />}
      {erro && <div className="integracao-erro">{erro}</div>}

      {!loading && semConta && (
        <section className="surface-card details-card">
          <p>Nenhuma conta do Meta Ads conectada nesta empresa.</p>
          {user?.usuAdmin ? (
            <Link to="/integracoes/meta-ads">Conectar uma conta em Integrações → Meta Ads</Link>
          ) : (
            <p className="muted-text">Peça a um administrador para conectar a conta em Integrações → Meta Ads.</p>
          )}
        </section>
      )}

      {!loading && painel && !semConta && t && (
        <>
          <section className="dashboard-cards-row campanhas-cards">
            {[
              ["Investimento", moeda(t.investimento)],
              ["Leads CRM", String(t.leadsCrm)],
              ["CPL", moeda(t.cpl)],
              ["Vendas", String(t.vendas)],
              ["CAC", moeda(t.cac)],
              ["MRR", moeda(t.mrr)],
              ["Retorno", multiplicador(t.retorno)],
            ].map(([rotulo, valor]) => (
              <div key={rotulo} className="dashboard-card">
                <strong className="dashboard-card-value">{valor}</strong>
                <span className="dashboard-card-label">{rotulo}</span>
              </div>
            ))}
          </section>

          <section className="surface-card campanhas-tabela-card">
            <div className="campanhas-tabela-scroll">
              <table className="dashboard-ranking-table campanhas-tabela">
                <thead>
                  <tr>
                    <th>Campanha</th>
                    <th>Status</th>
                    <th>Investimento</th>
                    <th>Impressões</th>
                    <th>Cliques</th>
                    <th>CTR</th>
                    <th>CPC</th>
                    <th>Leads Meta</th>
                    <th>Leads CRM</th>
                    <th>CPL</th>
                    <th>Vendas</th>
                    <th>CAC</th>
                    <th>MRR</th>
                    <th>Projeto</th>
                    <th title="(MRR × 12 + Projeto) ÷ Investimento">Retorno</th>
                  </tr>
                </thead>
                <tbody>
                  {painel.campanhas.length === 0 && !painel.naoIdentificada ? (
                    <tr>
                      <td colSpan={15} className="muted-text">
                        Sem investimento nem leads no período.
                      </td>
                    </tr>
                  ) : null}
                  {painel.campanhas.map((l) => linhaTabela(l, { clicavel: true }))}
                  {painel.naoIdentificada ? linhaTabela(painel.naoIdentificada, { clicavel: false, classe: "campanhas-linha-nao-identificada" }) : null}
                </tbody>
                <tfoot>{linhaTabela(t, { clicavel: false, classe: "campanhas-linha-total" })}</tfoot>
              </table>
            </div>
          </section>
        </>
      )}

      <CampanhaDetalheModal mcgId={detalheId} inicio={inicio} fim={fim} onClose={() => setDetalheId(null)} />
    </Layout>
  );
};

export default CampanhasPage;
```

- [ ] **Step 3: Rota, menu e estilos**

Em `frontend/src/App.tsx`: `import CampanhasPage from "./pages/Campanhas/CampanhasPage";` e, depois da rota `/oportunidades-kanban`:

```tsx
      <Route
        path="/campanhas"
        element={
          <ProtectedRoute>
            <CampanhasPage />
          </ProtectedRoute>
        }
      />
```

Em `frontend/src/components/Layout.tsx`, no grupo CRM, depois do `NavLink` de `/oportunidades-kanban`:

```tsx
                <NavLink to="/campanhas" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Campanhas
                </NavLink>
```

No fim de `frontend/src/styles.css`:

```css
/* ---- Meta Ads: página Campanhas e faixa do Dashboard ---- */
.campanhas-filtros {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.75rem;
}

.campanhas-cards .dashboard-card {
  min-width: 140px;
}

.campanhas-tabela-scroll {
  overflow-x: auto;
}

.campanhas-tabela th,
.campanhas-tabela td {
  white-space: nowrap;
}

.campanhas-tabela .campanhas-col-nome {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.campanhas-linha-nao-identificada td {
  color: #64748b;
  font-style: italic;
}

.campanhas-linha-total td {
  font-weight: 600;
  border-top: 2px solid #e2e8f0;
}

.campanha-detalhe-kpis {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
  color: #64748b;
  font-size: 0.85rem;
}

.campanha-detalhe-kpis strong {
  display: block;
  color: #0f172a;
  font-size: 1rem;
}

.campanha-grafico svg {
  width: 100%;
  height: auto;
  max-height: 200px;
}

.campanha-grafico-barra {
  fill: #93c5fd;
}

.campanha-grafico-linha {
  fill: none;
  stroke: #f97316;
  stroke-width: 2;
}

.campanha-grafico-legenda {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  margin: 0.25rem 0 1rem;
}

.campanha-legenda-barra,
.campanha-legenda-linha {
  display: inline-block;
  width: 12px;
  height: 8px;
  background: #93c5fd;
}

.campanha-legenda-linha {
  height: 2px;
  background: #f97316;
  margin-left: 0.6rem;
}

.dashboard-meta-ads {
  margin-top: 1rem;
}

.dashboard-meta-ads-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.5rem;
}
```

- [ ] **Step 4: Verificar tipos e build**

Run (em `frontend/`): `npx tsc --noEmit -p . 2>&1 | grep -c "error TS"`
Expected: `6`.
Run: `npm run build`
Expected: build sem erro.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Campanhas frontend/src/App.tsx frontend/src/components/Layout.tsx frontend/src/styles.css
git commit -m "Meta Ads: página Campanhas com detalhe diário e leads

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Faixa do Dashboard e campo no detalhe do lead

**Files:**
- Create: `frontend/src/components/metaAds/MetaAdsResumoFaixa.tsx`, `frontend/src/components/metaAds/CampanhaMetaField.tsx`
- Modify: `frontend/src/pages/Dashboard/DashboardPage.tsx` (import + inserir a faixa entre o fechamento da `<section className="dashboard-cards-row">` e `{/* Charts */}`), `frontend/src/pages/Oportunidades/OportunidadeDetalhePage.tsx` (interface + campo no grupo "Solução e origem")

**Interfaces:**
- Consumes: `GET /meta-ads/resumo`, `GET /meta-ads/campanhas-opcoes`, `PATCH /meta-ads/oportunidades/{id}/campanha` (Task 8); formatadores da Task 9.

- [ ] **Step 1: Faixa** — `frontend/src/components/metaAds/MetaAdsResumoFaixa.tsx`

```tsx
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { MetaAdsResumo, moeda, multiplicador } from "../../pages/Campanhas/metaAdsTipos";

const MetaAdsResumoFaixa: React.FC<{ dataInicial: string | null; dataFinal: string | null }> = ({ dataInicial, dataFinal }) => {
  const { api } = useAuth();
  const [resumo, setResumo] = useState<MetaAdsResumo | null>(null);

  useEffect(() => {
    api
      .get<MetaAdsResumo>("/meta-ads/resumo", {
        params: { data_inicial: dataInicial || undefined, data_final: dataFinal || undefined },
      })
      .then((r) => setResumo(r.data))
      .catch(() => setResumo(null));
  }, [api, dataInicial, dataFinal]);

  if (!resumo?.temConta) return null;

  const cards: Array<[string, string]> = [
    ["Investimento Meta", moeda(resumo.investimento)],
    ["CPL", moeda(resumo.cpl)],
    ["CAC", moeda(resumo.cac)],
    ["Retorno", multiplicador(resumo.retorno)],
  ];
  return (
    <section className="dashboard-meta-ads">
      <div className="dashboard-meta-ads-header">
        <h2 className="section-title">Meta Ads</h2>
        <Link to="/campanhas">Ver campanhas</Link>
      </div>
      <div className="dashboard-cards-row">
        {cards.map(([rotulo, valor]) => (
          <div key={rotulo} className="dashboard-card">
            <strong className="dashboard-card-value">{valor}</strong>
            <span className="dashboard-card-label">{rotulo}</span>
          </div>
        ))}
      </div>
    </section>
  );
};

export default MetaAdsResumoFaixa;
```

No `DashboardPage.tsx`: `import MetaAdsResumoFaixa from "../../components/metaAds/MetaAdsResumoFaixa";` e, logo após o `</section>` que fecha `dashboard-cards-row` (antes de `{/* Charts */}`):

```tsx
          <MetaAdsResumoFaixa dataInicial={dataInicial} dataFinal={dataFinal} />
```

- [ ] **Step 2: Campo** — `frontend/src/components/metaAds/CampanhaMetaField.tsx`

```tsx
import React, { useEffect, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";

interface Opcao {
  mcgId: number;
  nome: string;
  conta: string;
  status: string | null;
}

const CampanhaMetaField: React.FC<{
  opoId: number;
  opoMcgId: number | null;
  opoMcgManual: boolean;
  onSalvo: () => void;
}> = ({ opoId, opoMcgId, opoMcgManual, onSalvo }) => {
  const { api } = useAuth();
  const [opcoes, setOpcoes] = useState<Opcao[] | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    api
      .get<{ items: Opcao[] }>("/meta-ads/campanhas-opcoes")
      .then((r) => setOpcoes(r.data.items ?? []))
      .catch(() => setOpcoes([]));
  }, [api]);

  if (opcoes === null || (opcoes.length === 0 && opoMcgId == null)) return null;

  const salvar = async (valor: string) => {
    setSalvando(true);
    try {
      await api.patch(`/meta-ads/oportunidades/${opoId}/campanha`, { opoMcgId: valor ? Number(valor) : null });
      onSalvo();
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="info-item">
      <span className="info-label">Campanha Meta</span>
      <select
        className="detail-inline-input"
        value={opoMcgId ?? ""}
        disabled={salvando}
        onChange={(e) => void salvar(e.target.value)}
      >
        <option value="">Nenhuma</option>
        {opcoes.map((o) => (
          <option key={o.mcgId} value={o.mcgId}>
            {o.nome}
            {o.status && o.status !== "ACTIVE" ? " (inativa)" : ""}
          </option>
        ))}
      </select>
      {opoMcgId != null && !opoMcgManual ? <span className="field-hint">Vinculada automaticamente</span> : null}
    </div>
  );
};

export default CampanhaMetaField;
```

No `OportunidadeDetalhePage.tsx`:
- Na interface `OportunidadeDetail` (perto de `opoCcoId: number | null;`), adicionar `opoMcgId: number | null;` e `opoMcgManual: boolean;`.
- `import CampanhaMetaField from "../../components/metaAds/CampanhaMetaField";`
- No grupo "Solução e origem", depois do `info-item` de "Como conheceu" (antes do `</div>` que fecha `detail-field-group-grid`):

```tsx
                      {oportunidade && (
                        <CampanhaMetaField
                          opoId={oportunidade.opoId}
                          opoMcgId={oportunidade.opoMcgId ?? null}
                          opoMcgManual={Boolean(oportunidade.opoMcgManual)}
                          onSalvo={() => void loadOportunidade()}
                        />
                      )}
```

(Conferir o nome da variável de estado da oportunidade na página — é `oportunidade`, conforme `setDetalheCcoId(oportunidade.opoCcoId ?? null)` na linha ~293.)

- [ ] **Step 3: Verificar tipos e build**

Run (em `frontend/`): `npx tsc --noEmit -p . 2>&1 | grep -c "error TS"`
Expected: `6`.
Run: `npm run build`
Expected: build sem erro.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/metaAds frontend/src/pages/Dashboard/DashboardPage.tsx frontend/src/pages/Oportunidades/OportunidadeDetalhePage.tsx
git commit -m "Meta Ads: faixa no Dashboard e campanha no detalhe do lead

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Documentação, spec e verificação final

**Files:**
- Create: `docs/META_ADS.md`
- Modify: `docs/superpowers/specs/2026-10-14-meta-ads-campanhas-design.md` (seção nova "Ajustes na implementação")

- [ ] **Step 1: Guia de conexão** — `docs/META_ADS.md`

```markdown
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
```

- [ ] **Step 2: Registrar os ajustes na spec**

No fim de `docs/superpowers/specs/2026-10-14-meta-ads-campanhas-design.md`, adicionar uma seção `## 11. Ajustes na implementação` com os 9 itens da seção "Ajustes em relação à especificação" deste plano (copiar o texto, um item por linha) e mudar o **Status** do cabeçalho para `implementada`.

- [ ] **Step 3: Suíte completa do backend**

Run: `.venv/Scripts/python -m unittest $(ls backend/tests/test_*.py | sed 's#/#.#g; s#\.py$##' | tr '\n' ' ')`
Expected: todos OK (199 da base + os novos).

- [ ] **Step 4: Frontend**

Run (em `frontend/`): `npx tsc --noEmit -p . 2>&1 | grep -c "error TS"` → `6`; `npm run build` → sem erro.

- [ ] **Step 5: Verificação manual no app**

Com o ok do Carlos para a migration (Task 2, Step 6), subir backend e frontend, e conferir:
1. Integrações → Meta Ads: cadastrar uma conta com token real, "Testar conexão" mostra nome e moeda; "Sincronizar agora" passa a "OK" e o log mostra a carga inicial.
2. Campanhas: período "Ano atual" lista campanhas com investimento; a soma de Leads CRM + Vendas + MRR do Total bate com a linha da origem Meta na aba Fontes do Dashboard (quando todos os leads Meta usam essa origem).
3. Clicar numa campanha abre o gráfico diário e os leads com link.
4. Dashboard mostra a faixa Meta Ads; numa empresa sem conta, a faixa não aparece.
5. Detalhe de um lead: trocar a "Campanha Meta" salva e mostra o valor novo ao recarregar.

- [ ] **Step 6: Commit**

```bash
git add docs/META_ADS.md docs/superpowers/specs/2026-10-14-meta-ads-campanhas-design.md
git commit -m "Meta Ads: guia de conexão e ajustes registrados na spec

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
