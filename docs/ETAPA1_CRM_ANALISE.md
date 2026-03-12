# ETAPA 1 – Análise e mapeamento do módulo CRM

## 1. Estrutura atual analisada

### Backend
- **Framework:** FastAPI, SQLAlchemy, Alembic, JWT (python-jose), bcrypt.
- **Estrutura:** `models/`, `schemas/`, `routers/`, `services/`, `core/columns.py`, `core/mixins.py`.
- **Models:** Um arquivo por entidade. Uso de `IdColumnFactory`, `AtivoColumnFactory`, `AuditColumnFactory`. Multiempresa com FK para `empresa.empId` e `index=True`.
- **Schemas:** `*Base`, `*Create`, `*Update`, `*InDBBase`, `*Response`; listagem com `*ListResponse` (items, total, page, page_size).
- **Services:** Funções `list_*`, `get_*`, `create_*`, `update_*`, `delete_*` (soft delete por `cliAtivo = False`). Uso de `select()` e `func.count()`, sem `SELECT *`.
- **Routers:** Prefixo `/api/<recurso>`, `require_user_in_company(db, current_user, company_id)` em todos os endpoints, query params: `page`, `page_size`, `nome`, `status` (ativos|inativos|todos).
- **Dependencies:** `DbSessionDep`, `CurrentUserDep`, `CompanyIdDep`, `require_user_in_company`, `require_admin`.
- **Autenticação:** Header `X-Company-Id` injetado pelo frontend; backend valida vínculo em `usuario_empresa`.
- **Usuário:** Não existe CRUD de usuários na API (apenas `/auth/me`, login, refresh). Tabela `usuario` existe com usu/emp/use.

### Frontend
- **Stack:** React, TypeScript, Vite, axios via `useAuth().api`.
- **Layout:** Sidebar com `NavLink` (Dashboard, Clientes), `user`, `logout`, sem seletor de empresa visível no Layout (companyId existe no AuthContext).
- **Páginas:** `ClientesPage` = listagem (filtro nome/status, paginação), Modal criar/editar, ConfirmDialog excluir, DataTable.
- **Componentes reutilizáveis:** Layout, DataTable, Modal, Loader, ConfirmDialog.
- **Rotas:** `/`, `/clientes`, `/login`; ProtectedRoute envolve as autenticadas.

### Banco e migrations
- **Convenção:** Tabelas em português, singular, sem prefixo. Colunas `<alias>Campo`. Campos padrão: Id, EmpId (se multiempresa), Ativo, DataCriacao, DataAtualizacao.
- **Alembic:** `backend/alembic/versions/`, `from backend import models` no env.py. Migrations manuais com `op.create_table`, índices e FKs explícitos.

---

## 2. Aliases definitivos (novas tabelas)

| Tabela                   | Alias |
|--------------------------|-------|
| oportunidade             | opo   |
| como_conheceu            | cco   |
| motivo_cancelamento      | mca   |
| produto                  | pro   |
| etapa_kanban             | etk   |
| oportunidade_historico   | oph   |

Já existentes: usuario (usu), empresa (emp), usuario_empresa (use), cliente (cli).

---

## 3. Decisões técnicas

- **Ativar/Inativar:** O CRUD de Clientes usa `DELETE` que no service faz soft delete. Para o CRM foi pedido `PATCH .../ativar` e `PATCH .../inativar`; serão implementados nos novos recursos.
- **Usuário:** Não existe tela nem API de listagem/cadastro de usuários. Será criado router + service + schemas de usuário (somente leitura/edição, sem criar usuário sem senha) e tela de listagem/cadastro, respeitando a tabela existente.
- **Temperatura e Status:** `opoTemperatura` e `opoStatusFechamento` como `String(length=N)` com valores controlados no schema (evitar ENUM no banco para flexibilidade).
- **Seed etapas Kanban:** Incluído na migration de seed (após criar tabelas) com etapas padrão, por empresa padrão (empId=1).

---

## 4. Arquivos a criar/alterar

### Backend – Models
- `backend/models/como_conheceu.py` (novo)
- `backend/models/motivo_cancelamento.py` (novo)
- `backend/models/produto.py` (novo)
- `backend/models/etapa_kanban.py` (novo)
- `backend/models/oportunidade.py` (novo)
- `backend/models/oportunidade_historico.py` (novo)
- `backend/models/__init__.py` (alterar – exports)

### Backend – Schemas
- `backend/schemas/como_conheceu.py` (novo)
- `backend/schemas/motivo_cancelamento.py` (novo)
- `backend/schemas/produto.py` (novo)
- `backend/schemas/etapa_kanban.py` (novo)
- `backend/schemas/oportunidade.py` (novo)
- `backend/schemas/oportunidade_historico.py` (novo)
- `backend/schemas/usuario.py` (novo – expandir para CRUD se necessário)

### Backend – Services
- `backend/services/como_conheceu_service.py` (novo)
- `backend/services/motivo_cancelamento_service.py` (novo)
- `backend/services/produto_service.py` (novo)
- `backend/services/etapa_kanban_service.py` (novo)
- `backend/services/oportunidade_service.py` (novo)
- `backend/services/oportunidade_historico_service.py` (novo)
- `backend/services/usuario_service.py` (novo – list/get/create/update/ativar/inativar)

### Backend – Routers
- `backend/routers/como_conheceu_router.py` (novo)
- `backend/routers/motivo_cancelamento_router.py` (novo)
- `backend/routers/produto_router.py` (novo)
- `backend/routers/etapa_kanban_router.py` (novo)
- `backend/routers/oportunidade_router.py` (novo)
- `backend/routers/usuario_router.py` (novo)

### Backend – Main e migrations
- `backend/main.py` (alterar – incluir novos routers)
- `backend/alembic/versions/0003_crm_tables.py` (novo – tabelas CRM)
- `backend/alembic/versions/0004_seed_etapas_kanban.py` (novo – seed etapas) ou seed na mesma 0003

### Frontend – Páginas
- `frontend/src/pages/ComoConheceu/ComoConheceuPage.tsx` (novo)
- `frontend/src/pages/MotivoCancelamento/MotivoCancelamentoPage.tsx` (novo)
- `frontend/src/pages/Produtos/ProdutosPage.tsx` (novo)
- `frontend/src/pages/EtapasKanban/EtapasKanbanPage.tsx` (novo)
- `frontend/src/pages/Usuarios/UsuariosPage.tsx` (novo)
- `frontend/src/pages/Oportunidades/OportunidadesPage.tsx` (novo)
- `frontend/src/pages/Oportunidades/OportunidadeDetalhePage.tsx` (novo)

### Frontend – Rotas e layout
- `frontend/src/App.tsx` (alterar – rotas CRM e usuários)
- `frontend/src/components/Layout.tsx` (alterar – links menu CRM)

---

## 5. Riscos / dúvidas

- **Seletor de empresa:** O Layout atual não exibe seletor de empresa; o AuthContext já guarda `companyId`. Se não houver tela de seleção, o usuário precisa ter companyId definido por outro meio (ex.: primeiro login). Manter comportamento atual e, se necessário, adicionar seletor depois.
- **Permissão usuários:** CRUD de usuários pode ser restrito a admin; usar `require_admin` onde fizer sentido.
