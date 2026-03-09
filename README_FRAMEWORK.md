# Framework de Desenvolvimento Smart Data
## FastAPI + React + MySQL

Este documento descreve o **framework padrão de desenvolvimento utilizado pela Smart Data** para criação de sistemas internos e aplicações para clientes.

O objetivo é garantir que todos os projetos tenham:

- Arquitetura consistente
- Padronização de código
- Padronização de banco de dados
- Facilidade de manutenção
- Reaproveitamento entre projetos

Este framework pode ser utilizado como base para sistemas como:

- CRM
- ERP
- Sistemas internos
- Plataformas operacionais
- Sistemas de gestão

---

# 1. Estrutura geral do projeto

Todos os projetos seguem a seguinte estrutura base:
/backend
/frontend
README_FRAMEWORK.md
docker-compose.yml (opcional)


### Backend

Responsável por:

- API
- regras de negócio
- acesso ao banco
- autenticação

Tecnologias utilizadas:

- FastAPI
- SQLAlchemy
- Alembic
- JWT

---

### Frontend

Responsável por:

- interface do usuário
- comunicação com API
- componentes de interface

Tecnologias utilizadas:

- React
- TypeScript
- Vite

---

# 2. Backend

## Tecnologias

- FastAPI
- SQLAlchemy
- Alembic
- MySQL
- Pydantic
- JWT
- bcrypt

---

## Estrutura do backend
backend/
main.py
config.py
database.py
auth.py
models/
schemas/
routers/
services/
alembic/


---

### main.py

Responsável por:

- iniciar FastAPI
- configurar CORS
- registrar routers
- health check

Endpoints padrão:
/
/health
/api/health


---

### config.py

Centraliza todas as configurações do sistema.

Exemplos:
DATABASE_URL
JWT_SECRET_KEY
DEBUG
CORS_ORIGENS
LOG_LEVEL


Utiliza **pydantic-settings**.

---

### database.py

Responsável por criar:
engine
SessionLocal
Base


Também define a dependency padrão:
get_db()


---

### auth.py

Responsável por:

- autenticação
- geração de token
- validação de acesso

Tecnologias utilizadas:

- bcrypt
- python-jose

Fluxo:
login → valida senha → gera JWT


Dependências principais:
get_current_user
require_admin


---

# 3. Frontend

## Tecnologias

- React
- TypeScript
- Vite
- Axios

---

## Estrutura
frontend/src

components
pages
contexts
services
utils


---

### Configuração do Vite

Arquivo:


vite.config.ts


Proxy padrão:


/api → backend


---

### Descoberta da API

Arquivo:


src/utils/api.ts


Função principal:


getApiBaseUrl()


Responsável por:

- identificar ambiente
- resolver URL correta da API

---

### Padrão de chamadas HTTP

Sempre enviar:


Authorization: Bearer <token>


Exemplo:


axios.get(${API_URL}/usuarios)


---

# 4. Padrão de Modelagem de Banco de Dados

Todos os sistemas seguem um **padrão único de modelagem**, facilitando:

- leitura
- manutenção
- escrita de queries
- padronização entre projetos

---

## 4.1 Nome das tabelas

Regras:

- português
- singular
- sem prefixos técnicos (`tb_`, `tbl_`, etc.)

Exemplos:

| Tabela |
|------|
| usuario |
| empresa |
| cliente |
| demanda |
| reuniao |

---

## 4.2 Alias das tabelas (3 letras)

Cada tabela possui um **alias fixo de 3 letras**.

Esse alias é utilizado:

- nas colunas
- em queries SQL
- em joins

Exemplo:

| Tabela | Alias |
|------|------|
| usuario | usu |
| empresa | emp |
| cliente | cli |
| demanda | dem |
| reuniao | reu |

---

## 4.3 Nome das colunas

Formato padrão:


<alias><NomeCampo>


Exemplo:

Tabela `reuniao`


reuId
reuTitulo
reuData
reuTomReuniao
reuEmpId


Tabela `demanda`


demId
demNome
demDescricao
demPrjId


---

## 4.4 Campos padrão

Quase todas as tabelas devem possuir:


<alias>Id
<alias>EmpId (quando multiempresa)
<alias>DataCriacao
<alias>DataAtualizacao
<alias>Ativo


Exemplo:


reuId
reuEmpId
reuTitulo
reuData
reuAtivo
reuDataCriacao


---

# 5. Arquitetura Multiempresa

Os sistemas podem ser desenvolvidos em dois modelos.

---

## 5.1 Sistema Single Empresa

Utilizado quando o sistema atende **apenas uma empresa**.

Características:

- não possui campo empresa
- estrutura mais simples

Exemplo de tabelas:


usuario
cliente
demanda
reuniao


---

## 5.2 Sistema Multiempresa

Utilizado quando o sistema atende **múltiplas empresas dentro da mesma aplicação**.

Características:

- quase todas as tabelas possuem empresa
- usuários podem acessar múltiplas empresas

Exemplo:

Tabela `demanda`


demId
demEmpId
demNome
demDescricao


---

### Header utilizado


X-Company-Id


---

### Fluxo de requisição

1. Usuário faz login  
2. Recebe JWT  

Frontend envia:


Authorization: Bearer <token>
X-Company-Id: <empresa>


Backend:

- valida token
- valida acesso à empresa

---

### Controle de acesso

Tabela de vínculo:


usuario_empresa


Campos:


useId
useUsuId
useEmpId


---

### Regra importante

Todo novo projeto deve definir logo no início:


Sistema será multiempresa?


Essa decisão impacta:

- estrutura do banco
- autenticação
- queries
- performance

---

# 6. Convenções SQL

---

## Alias sempre obrigatórios


SELECT
dem.demId,
dem.demNome,
reu.reuTitulo
FROM demanda dem
LEFT JOIN reuniao reu
ON reu.reuDemId = dem.demId


---

## Evitar SELECT *

Sempre especificar colunas.

---

## JOINs claros


FROM cliente cli
LEFT JOIN empresa emp
ON emp.empId = cli.cliEmpId


---

# 7. Migrações de banco

Utilizamos **Alembic**.

Estrutura:


backend/alembic
backend/alembic/versions


Fluxo:

### 1. Alterar models

### 2. Gerar migração


alembic revision --autogenerate -m "descricao"


### 3. Aplicar migração


alembic upgrade head


---

# 8. Estrutura recomendada de models

Evitar um único arquivo grande.

Preferir:


models/

usuario.py
empresa.py
cliente.py
demanda.py
reuniao.py


---

# 9. Template base de projeto

Todo novo sistema deve começar copiando o template base.

Backend:


config.py
database.py
auth.py
routers/
models/
schemas/
alembic/


Frontend:


AuthContext
Layout
Modal
DataTable
API utils


---

# 10. Objetivo deste framework

Garantir que todos os sistemas da Smart Data tenham:

- arquitetura consistente
- banco padronizado
- fácil manutenção
- desenvolvimento mais rápido
- reaproveitamento de código

------------------------------------------------------------------------
Demais considerações 

1. Núcleo de autenticação e acesso

Login com JWT

Refresh token

Recuperação e redefinição de senha

Controle de perfil e permissões

Controle de acesso por empresa, quando multiempresa

Middleware/dependency para usuário autenticado

Endpoint /me

Estrutura inicial de usuários, empresas e vínculo usuário-empresa

2. Estrutura base de banco

Tabelas padrão de autenticação

Tabela de sequência, se continuar sendo padrão de vocês

Campos padrão de auditoria

Convenção de soft delete ou ativo/inativo

Índices padrão

Exemplo de migrations iniciais

Seeds iniciais de usuário admin, perfil e empresa padrão

3. Padrão de arquitetura backend

Separação clara entre models, schemas, routers, services, repositories se quiserem adotar

Arquivo base de configurações por ambiente

Tratamento centralizado de exceções

Respostas padronizadas da API

Health check

Logs estruturados

Validações reutilizáveis

Paginação padrão

Filtros e ordenação padrão

4. Padrão de arquitetura frontend

Fluxo completo de autenticação

Proteção de rotas

Layout autenticado base

Página de login

Página de troca/recuperação de senha

Contexto global de autenticação

Cliente HTTP centralizado com interceptor

Tratamento padrão de erro e sessão expirada

Estrutura base de páginas, componentes e serviços

Tema visual base da Smart Data

5. Componentes reutilizáveis

DataTable

Modal padrão

Formulário base

Inputs padronizados

Select com busca

Date picker

Status badge

Loader

Confirmação de exclusão

Empty state

Toast/alerta padrão

6. Padrão de CRUD

Estrutura padrão para listagem

Estrutura padrão para criação/edição

Filtros

Paginação

Exclusão lógica

Ativar/inativar registro

Convenção de endpoints REST

Convenção de nomes de arquivos e funções

7. Multiempresa

Modo single empresa e multiempresa já preparados

Chave para habilitar/desabilitar multiempresa no projeto

Company selector no frontend

Header X-Company-Id

Validação de acesso no backend

Guia de decisão: quando usar ou não multiempresa

8. Segurança

Hash de senha

Expiração de token

Política mínima de senha

Rate limit para login, se quiserem evoluir

CORS configurável

Variáveis de ambiente seguras

Proteção básica contra exposição de erros internos

Auditoria de login e ações sensíveis

9. Observabilidade e suporte

Logs padronizados

ID de requisição

Health check simples e detalhado

Estrutura para monitoramento futuro

Registro de erros

Base para auditoria de ações do usuário

10. Testes

Estrutura base de testes backend

Estrutura base de testes frontend

Testes de autenticação

Testes de permissões

Testes de CRUD

Massa de dados de teste

Exemplo de pipeline de validação

11. DevOps e ambiente

.env.example

scripts de setup

docker compose base

comandos padrão de subida local

padrão de build

padrão de deploy

checklist de publicação

separação entre dev, homolog e prod

12. Documentação operacional

README técnico

checklist para criar novo projeto

checklist para criar nova entidade

checklist para criar novo CRUD

padrão de nomenclatura

padrão de migration

padrão de branch e versionamento

guia para uso com Cursor

13. Base funcional inicial

Eu já deixaria um módulo pronto de exemplo com:

Usuários

Empresas

Vínculo usuário x empresa

Perfil/permissão

Tela de dashboard inicial vazia

CRUD exemplo completo para servir de referência

14. Itens que valem muito a pena desde o início

Esses aqui acho especialmente importantes para o seu cenário:

sistema de permissões desde a base

multiempresa opcional

CRUD padrão reutilizável

seed inicial automática

layout autenticado pronto

interceptor de API

tratamento padronizado de erros

checklist para o Cursor gerar novos módulos no mesmo padrão

A melhor forma de estruturar isso é dividir o framework em 5 pacotes conceituais:

autenticação e acesso

banco e convenções

backend base

frontend base

documentação e geradores de padrão