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
- `./scripts/test-containers.sh` passando
- `ruff check .` passando no escopo ativo; `notebooks/` é excluído por ser arquivo histórico

## Validação local

```bash
# Stack local estável
docker compose up --build

# Hot reload
docker compose -f compose.yaml -f compose.dev.yaml up --build

# Lint, typecheck, testes, builds e smoke HTTP
./scripts/test-containers.sh
```

Novas funcionalidades devem incluir testes offline no target do componente afetado. Se criarem
um processo, dependência operacional, volume ou serviço de rede, atualizar Compose, healthcheck e
smoke test na mesma entrega. Testes de provedores externos são opt-in e não entram na CI comum.

O diretório `notebooks/` e o manifesto de dependências da raiz pertencem à POC histórica. Não os
instale, corrija ou reexecute como parte do desenvolvimento do produto. Experimentos novos devem
ser reproduzíveis por código, fixtures e targets Docker no componente responsável.

Os comandos diretos no host permanecem documentados em
[`local-setup.md`](../operations/local-setup.md) para diagnóstico específico.
