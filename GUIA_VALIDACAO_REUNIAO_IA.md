# Guia de validacao - Reuniao / IA

## Pre-condicoes

- Backend atualizado com `alembic -c backend/alembic.ini upgrade head`
- Dependencias backend instaladas (`pip install -r backend/requirements.txt`)
- Variavel `LLM_OPENAI_API_KEY` configurada no `.env`
- Frontend em execucao e usuario autenticado
- Header `X-Company-Id` configurado pelo frontend

## Checklist funcional

1. Acessar detalhe de oportunidade e localizar secao **Reuniao / IA**.
2. Colar transcricao no textarea e clicar em **Processar com IA**.
3. Enviar apenas **Transcricao (arquivo)** (.txt ou .pdf com texto), sem texto no textarea, e processar.
4. Enviar texto + arquivo de transcricao e confirmar que ambos sao considerados (texto unido no backend).
5. Validar exibicao de status, resumo, feedback e sugestoes.
6. Repetir com **Materiais complementares** `.txt`, `.csv`, `.json` e `.pdf` textual.
7. Confirmar que historico lista novas analises com data e status.
8. Validar acao **Aplicar observacoes** e conferir `opoComentarios`.
9. Validar acao **Aplicar dores/oportunidades** e conferir `opoDoresMotivadores`.
10. Validar acao **Aplicar lead score** e conferir `opoLeadScore`.
11. Validar acao **Aplicar temperatura** e conferir `opoTemperatura`.
12. Enviar arquivo de transcricao nao suportado e confirmar erro amigavel.

## Validacao tecnica sugerida

- Executar testes:
  - `python -m unittest backend.tests.test_escopo_ai_service backend.tests.test_reuniao_analise_service`
- Compilar arquivos Python alterados:
  - `python -m compileall backend`
