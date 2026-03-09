## SD Framework - Visão Geral

Este repositório contém o **framework base** utilizado pela Smart Data para criação de novos sistemas web (CRM, ERP, sistemas internos, automações etc.).

Ele é intencionalmente **genérico de domínio**, focando em:

- **Arquitetura padronizada backend + frontend**
- **Modelo de banco de dados unificado**
- **Autenticação e multiempresa prontos**
- **Exemplo de CRUD completo**

Arquivos complementares:

- Consulte o `DATABASE_GUIDELINES.md` para detalhes de modelagem.
- Consulte o `API_GUIDELINES.md` para padrões de API e CRUD.

---

### 1. Setup do projeto

- Copie o repositório `sd-framework` como base do novo sistema.
- Crie o arquivo `.env` a partir de `.env.example`, ajustando:
  - `DATABASE_URL`
  - variáveis de JWT
  - `MULTIEMPRESA_ENABLED` (`true` ou `false`)

#### Rodando com Docker

No diretório raiz:

- `docker compose up -d --build`

Isso sobe:

- MySQL (`db`)
- Backend FastAPI (`backend` na porta 8000)
- Frontend React/Vite (`frontend` na porta 5173)

#### Rodando localmente (sem Docker)

Backend:

- `cd backend`
- `pip install -r requirements.txt`
- Configurar `DATABASE_URL` no `.env`
- `alembic upgrade head`
- `uvicorn main:app --reload`

Frontend:

- `cd frontend`
- `npm install`
- `npm run dev`

---

### 2. Migrações e seed inicial

- Migrações ficam em `backend/alembic/versions`.
- Para aplicar todas as migrações:

- `cd backend`
- `alembic upgrade head`

Seed padrão:

- Migration `0002_seed_initial_data` cria:
  - Empresa padrão (`empId = 1`, `empNome = "Empresa Padrão"`)
  - Usuário admin (`admin@smartdata.local`, senha `admin123`, `usuAdmin = true`, `usuPerfil = "admin"`)
  - Vínculo `usuario_empresa` entre esse usuário e a empresa padrão.

Após aplicar as migrações, já é possível:

- Fazer login no frontend com:
  - E-mail: `admin@smartdata.local`
  - Senha: `admin123`

> **Importante**  
> Este seed é pensado para **ambientes de desenvolvimento local**.  
> Em homologação e produção:
>
> - altere a senha do usuário admin imediatamente;
> - ou crie um fluxo próprio de criação de usuários/empresas e remova o seed padrão se não fizer sentido.

Se o sistema estiver em modo multiempresa, basta enviar `X-Company-Id: 1` nas requisições (o frontend pode ser adaptado para seleção de empresa).

---

### 3. Criação de novos módulos / CRUDs

Para criar uma nova entidade, siga este fluxo:

1. **Model** (`backend/models/<entidade>.py`)
   - Defina o nome da tabela em português e singular.
   - Defina o alias de 3 letras.
   - Crie as colunas seguindo `<alias><Campo>` e, quando aplicável:
     - `<alias>Id`
     - `<alias>EmpId`
     - `<alias>Ativo`
     - `<alias>DataCriacao`
     - `<alias>DataAtualizacao`
   - Reaproveite as fábricas de colunas em `backend/core/columns.py` para `Id`, `Ativo` e auditoria.

2. **Schema** (`backend/schemas/<entidade>.py`)
   - Crie modelos Pydantic para:
     - criação (`<Entidade>Create`)
     - atualização (`<Entidade>Update`)
     - resposta (`<Entidade>Response`)
     - listagem paginada se necessário.

3. **Service** (`backend/services/<entidade>_service.py`)
   - Centralize regras de negócio, filtros, paginação e soft delete (via `<alias>Ativo`).

4. **Router** (`backend/routers/<entidade>_router.py`)
   - Crie endpoints em `/api/<entidade-no-plural>`, usando:
     - `get_current_user`
     - `get_company_id_from_header` (se multiempresa)
     - `require_user_in_company` para validar acesso.

5. **Migração**
   - Atualize o model.
   - Gere uma migration:
     - `alembic revision --autogenerate -m "add <entidade>"`
   - Revise se a migration está coerente com o padrão Smart Data.

6. **Frontend**
   - Crie página em `frontend/src/pages/<EntidadePlural>/`.
   - Use:
     - `AuthContext` para autenticação.
     - `api` (axios) para chamadas HTTP.
     - Componentes base (`Layout`, `DataTable`, `Modal`, `ConfirmDialog`, `Loader`).
   - Implemente filtros, paginação e soft delete (inativando registros via campo `<alias>Ativo`).

---

### 4. Padrões oficiais do framework

- **Autenticação**
  - Backend:
    - Login com JWT (`/api/auth/login`).
    - Refresh token (`/api/auth/refresh`).
    - Endpoint `/api/auth/me` para obter o usuário autenticado.
  - Frontend:
    - `AuthContext` gerencia `access_token` e `refresh_token`.
    - Cliente HTTP (`api`) renova o access token automaticamente em caso de `401`, via `/auth/refresh`.
    - Em falha de refresh, realiza logout centralizado e redireciona para `/login`.

- **CRUD**
  - Endpoints REST convencionais (`GET`, `POST`, `PUT`, `DELETE`).
  - Soft delete:
    - `DELETE` inativa registros via `<alias>Ativo = false`.
    - Listagens retornam **apenas ativos** por padrão.
    - Parâmetros permitem listar somente inativos ou todos.
  - Paginação e filtros:
    - parâmetros padrão `page`, `page_size` e campos específicos (ex.: `nome`, `status`).

- **Single empresa vs multiempresa**
  - Definido via `MULTIEMPRESA_ENABLED` no `.env`:
    - `false` → sistema single empresa (não exige `X-Company-Id`).
    - `true` → sistema multiempresa (exige `X-Company-Id` e valida acesso do usuário).
  - Tabelas multiempresa usam o campo `<alias>EmpId`.
  - A validação de acesso por empresa é feita através da tabela `usuario_empresa` e da dependency `require_user_in_company`.


