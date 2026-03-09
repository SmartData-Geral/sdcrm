## Padrão de APIs e CRUD - SD Framework

### 1. Convenções Gerais

- APIs RESTful, versionadas por prefixo `/api`.
- Recursos em **português**, seguindo o domínio (ex.: `/clientes`, `/usuarios`).
- Uso consistente de:
  - `GET /api/recurso`
  - `GET /api/recurso/{id}`
  - `POST /api/recurso`
  - `PUT /api/recurso/{id}`
  - `DELETE /api/recurso/{id}` (soft delete via campo `<alias>Ativo` quando aplicável).

### 2. Autenticação

Endpoints base:

- `POST /api/auth/login`
- `GET /api/auth/me`

Padrão de headers:

- `Authorization: Bearer <token>`
- `X-Company-Id: <empresa>` (quando multiempresa habilitado)

### 3. Padrão de Respostas

- Sucesso:
  - `200` / `201` com payload JSON.
- Erros:
  - `400` – erro de validação/regra de negócio.
  - `401` – não autenticado.
  - `403` – sem permissão/acesso à empresa.
  - `404` – recurso não encontrado.

### 4. Padrão de CRUD

Cada módulo segue a separação:

- `models/` – modelos SQLAlchemy (entidades).
- `schemas/` – modelos Pydantic (entrada/saída).
- `services/` – regras de negócio e orquestração.
- `routers/` – exposição HTTP dos serviços.

O módulo de exemplo `cliente` implementa:

- Modelagem seguindo alias `cli`.
- Filtro por empresa (quando multiempresa).
- Campos padrão de auditoria.

#### Soft delete (padrão oficial)

- `DELETE /api/recurso/{id}` **não remove fisicamente** o registro.
- O endpoint deve:
  - marcar `<alias>Ativo = false`;
  - manter os dados para histórico/auditoria.
- Listagens (`GET /api/recurso`) devem:
  - por padrão retornar **apenas registros ativos**;
  - oferecer parâmetros para:
    - listar somente inativos;
    - listar todos (ativos + inativos).

No exemplo de `cliente`:

- Campo de soft delete: `cliAtivo`.
- Parâmetro de status: `status=ativos|inativos|todos` em `GET /api/clientes`.


