# Guia Completo de Acesso (Backend + Frontend)

Este documento descreve o passo a passo completo para:

1. preparar ambiente
2. subir backend e frontend
3. validar acesso pela API e pela tela de login

## 1) Pre-requisitos

- Python 3.12+
- Node.js 18+
- MySQL acessivel
- Ambiente virtual Python criado em `.venv`

## 2) Configuracao do `.env`

No arquivo `.env` da raiz do projeto, confirme:

```env
DATABASE_URL=mysql+pymysql://USUARIO:SENHA@HOST:3306/sdcrm
BACKEND_PORT=8000
FRONTEND_PORT=5173
ALLOW_ORIGINS=http://localhost:5173
```

Importante:
- O backend e o Alembic usam `DATABASE_URL` como fonte principal.
- Garanta que o schema correto seja `sdcrm`.

## 3) Aplicar migracoes do backend

Na raiz do projeto:

```powershell
cd "C:\Users\carlo\Documents\Sistemas\framework"
.\.venv\Scripts\Activate.ps1
alembic -c backend\alembic.ini upgrade head
```

Resultado esperado no terminal:
- upgrade para `0001_initial`
- upgrade para `0002_seed_initial_data`

## 4) Subir o backend (API)

Ainda na raiz do projeto:

```powershell
cd "C:\Users\carlo\Documents\Sistemas\framework"
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Resultado esperado:
- API em `http://127.0.0.1:8000`
- log com `Application startup complete`

## 5) Validar backend (acesso API)

Com backend rodando:

- `GET http://127.0.0.1:8000/health` -> `{"status":"ok"}`
- `GET http://127.0.0.1:8000/api/health` -> `{"status":"ok"}`

Teste de login pela API:

- `POST http://127.0.0.1:8000/api/auth/login`
- Body JSON:

```json
{
  "email": "admin@smartdata.local",
  "senha": "admin123"
}
```

Resultado esperado:
- resposta `200`
- retorno com `access_token` e `refresh_token`

## 6) Subir o frontend

Em outro terminal:

```powershell
cd "C:\Users\carlo\Documents\Sistemas\framework\frontend"
npm install
npm run dev
```

Resultado esperado:
- Frontend em `http://localhost:5173`
- Vite com status `ready`

## 7) Validar integracao frontend -> backend

Com ambos rodando:

- `GET http://localhost:5173/api/health` -> `{"status":"ok"}`

Isso confirma que o proxy do frontend para o backend esta funcional.

## 8) Testar acesso completo pela interface (frontend)

1. Abrir `http://localhost:5173`
2. Na tela de login, informar:
   - E-mail: `admin@smartdata.local`
   - Senha: `admin123`
3. Clicar em **Entrar**

Resultado esperado:
- login realizado com sucesso
- redirecionamento para a area autenticada (dashboard)

## 9) Credenciais de desenvolvimento (seed)

- E-mail: `admin@smartdata.local`
- Senha: `admin123`

Obs.: estas credenciais sao de ambiente local/de desenvolvimento.

## 10) Problemas comuns e solucao

- `ModuleNotFoundError: No module named 'backend'`
  - Execute o backend a partir da raiz `framework`:
    - `uvicorn backend.main:app --reload --port 8000`

- Erro `email-validator is not installed`
  - Reinstale dependencias:
    - `pip install -r backend\requirements.txt`

- Alembic com revisao inexistente
  - Verifique a tabela `alembic_version` no banco e alinhe com as revisoes do projeto.

- Frontend abre, mas login falha
  - Verifique:
    - backend ativo em `http://127.0.0.1:8000`
    - schema correto em `DATABASE_URL`
    - usuario seed criado (`admin@smartdata.local`)

