# Desenvolvimento

## Branches

- `main` — produção estável; nunca commitar diretamente.
- `feat/<escopo>` — nova funcionalidade.
- `fix/<escopo>` — correção de bug.
- `chore/<escopo>` — manutenção, dependências, docs.

## Commits

Formato Conventional Commits: `tipo(escopo): descrição` (máx 72 chars, imperativo).

Tipos: `feat fix chore docs refactor test ci perf`.

Exemplos:
```
feat(evaluation): adicionar dimensão de interdisciplinaridade ao prompt
fix(parser): corrigir extração de PDFs com encoding não-UTF8
docs(rag): documentar métricas de validação de recuperação
```

## Pull Request

Usar o template em `.github/PULL_REQUEST_TEMPLATE.md`.

Checklist antes de abrir PR:
- `ruff check .` sem erros
- `pytest` passando
- notebooks relevantes re-executados se houver mudança de parâmetros

## Validação local

```bash
# Lint
ruff check .

# Testes
pytest

# Serviço
cd qa-services && uvicorn app.main:app --reload --port 8000

# Frontend
cd qa-application && npm start
```
