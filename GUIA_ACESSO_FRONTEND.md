# Guia Completo de Acesso (Backend + Frontend)

Este documento descreve o passo a passo completo para:

1. preparar ambiente
2. subir backend e frontend
3. validar acesso pela API e pela tela de login

## Deploy:
cd /opt/smartdata/crm/sdcrm
git status
git pull origin main
docker compose up -d --build
docker ps

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
cd "sdcrm"
.\.venv\Scripts\Activate.ps1
alembic -c backend\alembic.ini upgrade head
```

Resultado esperado no terminal:
- upgrade para `0001_initial`
- upgrade para `0002_seed_initial_data`

## 4) Subir o backend (API)

Ainda na raiz do projeto:

```powershell
cd "sdcrm"
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.main:app --reload --port 8000
```
```powershell
.\.venv\Scripts\Activate.ps1

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
cd frontend
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

## 11) Publicacao em producao (frontend em `/crm`)

Para ambiente publicado, use estas variaveis no build do frontend:

```env
VITE_API_BASE_URL=/crm/api
VITE_PUBLIC_BASE_URL=https://SEU_DOMINIO/crm
```

Notas:
- `VITE_PUBLIC_BASE_URL` deve ser URL absoluta para o link externo da proposta.
- No `docker-compose.yml`, os `build args` do frontend ja aceitam ambas as variaveis.

No Nginx do frontend, mantenha o proxy para backend antes da rota SPA:

```nginx
location /crm/api/ {
    proxy_pass http://crm-backend:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /crm/static/ {
    proxy_pass http://crm-backend:8000/static/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /crm/public/ {
    proxy_pass http://crm-backend:8000/public/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /crm/ {
    alias /usr/share/nginx/html/;
    try_files $uri $uri/ /crm/index.html;
}
```

Checklist rapido apos publicar:
1. Upload e exibicao de avatar no cadastro de usuarios.
2. Preview de logo da empresa no cadastro de empresas.
3. Imagens da proposta (apresentacao/clientes) no preview e na pagina publica.
4. Link da proposta copiado e aberto em aba anonima/dispositivo externo.
5. Registro de visualizacao/aceite da proposta no backend.

## 12) Fluxo de templates de proposta (snapshot)

Fluxo oficial atual:

1. Monte e edite uma proposta normalmente.
2. Na tela do editor da proposta, use a acao **Salvar como template**.
3. Informe:
   - nome do template
   - produto/solucao
   - tipo da proposta
   - ativo
   - padrao (opcional)
4. O sistema cria um template com snapshot de:
   - `prpJsonConfiguracao` da proposta
   - blocos da proposta
5. Ao criar uma nova proposta e escolher um template, a proposta nasce clonada do snapshot.

Regras importantes:

- Template e proposta sao independentes apos a criacao.
- Alterar proposta nao altera template.
- Alterar template nao altera propostas ja criadas.
- Sem template selecionado, o sistema usa os defaults internos de proposta.

