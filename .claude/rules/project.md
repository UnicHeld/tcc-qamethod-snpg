# Convenções do Projeto

`AGENTS.md` é a fonte canônica das regras gerais. Este arquivo mantém reforços usados
automaticamente pelo Claude.

## Estrutura

| Módulo | Responsabilidade |
|---|---|
| `qa-services/app/services/` | lógica de domínio: método QA, RAG, scoring |
| `qa-services/app/routers/` | endpoints HTTP — apenas roteamento |
| `qa-services/app/core/` | configuração, dependências, clientes |
| `qa-application/src/` | interface React |
| `notebooks/` | análise exploratória e validação estatística |

## Python

- Regra de negócio em `services/`; routers não contêm lógica de domínio.
- Clientes externos (Qdrant, LLM APIs) isolados em `core/` ou módulos dedicados.
- Validar entrada externa; não registrar segredos ou dados pessoais.

## Commits

- Usar Conventional Commits.
- Tipos: `feat fix chore docs refactor test ci perf`.
