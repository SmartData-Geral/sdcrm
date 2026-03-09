## Padrão de Banco de Dados - Smart Data

Este documento resume e reforça o padrão de modelagem utilizado em todos os projetos que usam o **SD Framework**.

### 1. Tabelas

- **Português**
- **Singular**
- **Sem prefixos técnicos** (`tb_`, `tbl_` etc.)

Exemplos: `usuario`, `empresa`, `cliente`, `demanda`, `reuniao`.

Cada tabela possui um **alias fixo de 3 letras**, que é usado:

- No prefixo de colunas
- Em queries SQL
- Em joins

Exemplos:

- `usuario` → `usu`
- `empresa` → `emp`
- `cliente` → `cli`

### 2. Colunas

Formato obrigatório:

- `<alias><Campo>`

Campos padrão recomendados:

- `<alias>Id`
- `<alias>EmpId` (quando multiempresa)
- `<alias>DataCriacao`
- `<alias>DataAtualizacao`
- `<alias>Ativo`

### 3. Multiempresa

- Modo **single empresa**: tabelas não possuem campo de empresa.
- Modo **multiempresa**: tabelas possuem `<alias>EmpId` e o acesso é filtrado por empresa.

O framework já traz:

- Tabelas `usuario`, `empresa`, `usuario_empresa`, `cliente`.
- Validação de acesso à empresa via tabela `usuario_empresa`.

