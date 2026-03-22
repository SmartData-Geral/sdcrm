# Guia de validacao - Geracao de Escopo com IA

Este checklist valida a funcionalidade de geracao de escopo via IA no editor de propostas.

## Pre-condicoes

- Backend com dependencias atualizadas (`pip install -r backend/requirements.txt`)
- Frontend em execucao
- Variavel `LLM_OPENAI_API_KEY` configurada no `.env`
- Usuario autenticado com acesso a empresa selecionada

## Checklist manual

1. Abrir uma proposta e acessar a aba **Escopo Inicial**.
2. Na caixa **Geracao de escopo com IA**, anexar um arquivo `.txt` e clicar em **Gerar escopo com IA**.
3. Verificar que os cards foram preenchidos automaticamente.
4. Repetir com um arquivo `.json` valido e conferir preenchimento dos cards.
5. Repetir com um arquivo `.pdf` com texto selecionavel e conferir preenchimento.
6. Repetir com uma imagem (`.png` ou `.jpg`) contendo texto descritivo e conferir preenchimento.
7. Tentar enviar um tipo nao suportado (ex.: `.docx`) e validar retorno de erro amigavel.
8. Tentar enviar arquivo maior que o limite configurado e validar erro de limite.
9. Conferir que ainda e possivel editar manualmente os cards apos a geracao.

## Validacao tecnica sugerida

- Rodar testes unitarios de servico:
  - `python -m unittest backend.tests.test_escopo_ai_service`
