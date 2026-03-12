# ETAPA 6 – Revisão e pendências para próxima fase

## O que foi criado

### Backend
- **Models:** `como_conheceu`, `motivo_cancelamento`, `produto`, `etapa_kanban`, `oportunidade`, `oportunidade_historico` (um arquivo por entidade).
- **Schemas:** Um arquivo de schemas por entidade (Base, Create, Update, InDBBase, Response, ListResponse); schemas de usuário para CRUD; request bodies para mover-etapa, lead-score e temperatura.
- **Services:** Serviços para todas as entidades, com list (filtros, paginação), get, create, update, ativar/inativar; oportunidade com ganhar/perder/stand-by, mover-etapa, lead-score, temperatura, reunião/proposta; histórico com list, create, update, inativar.
- **Routers:** Rotas para como-conheceu, motivos-cancelamento, produtos, etapas-kanban, oportunidades, historicos-oportunidade, usuarios (admin). Todos com `require_user_in_company` e, no caso de usuários, `require_admin`.
- **Migrations:** `0003_crm_tables` (tabelas CRM com FKs e índices), `0004_seed_etapas_kanban` (etapas padrão para empresa 1).

### Frontend
- **Páginas:** ComoConheceu, MotivoCancelamento, Produtos, EtapasKanban, Usuarios (admin), Oportunidades (listagem + modal cadastro/edição), OportunidadeDetalhePage (cabeçalho, temperatura, lead score, botões ganhar/perder/stand-by, bloco de detalhes, bloco de histórico, modal adicionar histórico).
- **Rotas:** `/como-conheceu`, `/motivos-cancelamento`, `/produtos`, `/etapas-kanban`, `/usuarios`, `/oportunidades`, `/oportunidades/:opoId`.
- **Layout:** Menu CRM com links para todas as páginas; “Usuários” só para admin; estilo `.sidebar-nav-group` e botão `.success`.

### Decisões técnicas
- Cadastros CRM usam **PATCH ativar / PATCH inativar** (diferente do Clientes que usa DELETE para inativar).
- **Temperatura** e **status de fechamento** em colunas string (sem ENUM no banco).
- **Usuário:** CRUD só para admin; listagem filtrada por empresa (join com `usuario_empresa`).
- **Histórico:** `ophDataRegistro` com valor no insert; `ophUsuId` preenchido com o usuário autenticado no create.
- **Seed etapas:** Apenas para `empId = 1`; etapas em ordem com nome e cor.

---

## O que foi alterado

- **backend/main.py:** Inclusão dos novos routers (como_conheceu, motivo_cancelamento, produto, etapa_kanban, oportunidade, historico_oportunidade, usuario).
- **backend/models/__init__.py:** Export dos novos models.
- **frontend/App.tsx:** Novas rotas para as páginas CRM e usuários.
- **frontend/components/Layout.tsx:** Novos links no menu e grupo “CRM”; link Usuários condicionado a `user?.usuAdmin`.
- **frontend/styles.css:** Classe `.sidebar-nav-group` e botão `.success`.

---

## Pendências para próxima fase

Itens sugeridos para evolução do módulo CRM:

1. **Kanban visual**  
   Tela de oportunidades em colunas por etapa (drag-and-drop ou mudança de etapa por dropdown).

2. **Visualização em tabela**  
   Melhorias na listagem (ordenação por coluna, filtros por etapa/responsável/status de fechamento, exportação).

3. **Geração de proposta**  
   Fluxo e modelo de proposta (documento/PDF) vinculado à oportunidade.

4. **Geração de contrato**  
   Modelo de contrato e geração a partir da oportunidade ganha.

5. **Dashboard**  
   Indicadores (pipeline por etapa, valor, taxa de conversão, atividades recentes).

6. **Análise com IA**  
   Sugestões de próxima ação, score de lead ou resumos a partir do histórico.

7. **Seletor de empresa**  
   Se o sistema tiver mais de uma empresa, exibir no Layout o seletor de empresa (X-Company-Id) e garantir companyId após login.

8. **Motivo de cancelamento ao perder**  
   Ao marcar oportunidade como “Perdida”, permitir escolher motivo (opoMcaId) e opcionalmente registrar no histórico.

9. **Campos de valor**  
   Se houver valor da oportunidade, incluir campo (ex.: opoValor) e usar em dashboard e propostas.

10. **Rich text no histórico**  
    Trocar textarea do histórico por editor rich text, se já houver componente no projeto.

---

## Como rodar

- **Backend:** Na raiz do projeto, ativar o venv e rodar `alembic -c backend\alembic.ini upgrade head` (se ainda não aplicou). Depois `uvicorn backend.main:app --reload --port 8000`.
- **Frontend:** Em `frontend`, `npm install` e `npm run dev`.
- **Login:** `admin@smartdata.local` / `admin123` (seed). Definir empresa (ex.: 1) se o frontend enviar X-Company-Id; do contrário garantir que o backend não exija company em modo dev ou que o contexto defina companyId.

---

## Riscos / observações

- **CompanyId:** Se MULTIEMPRESA_ENABLED for true e o frontend não enviar X-Company-Id, as requisições aos endpoints que usam `CompanyIdDep` falham com 400. É necessário definir companyId no AuthContext (ex.: após login ou por seletor).
- **Usuários sem empresa:** Listagem de usuários filtra por empresa; usuários sem vínculo na empresa atual não aparecem. Admin pode precisar de tela de vínculo usuário–empresa.
- **Permissões:** Além de admin para usuários, não há restrição por perfil nas outras telas; todos os usuários autenticados da empresa podem ver e editar oportunidades e cadastros.
