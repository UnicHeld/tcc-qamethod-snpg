# Notebooks preservados apenas como arquivo histórico da POC

- Status: `aceita`.
- Data: 2026-09-13.
- [System design](../architecture/prototype-recovery-design.md).
- [Roteiro de recuperação](../specs/prototype-recovery.md).

## Contexto

Os notebooks foram usados na prova de conceito inicial. Eles têm dependências, caminhos e
experimentos que não representam o runtime recuperado nem a estratégia vigente de validação.
Mantê-los no escopo ativo faria a qualidade do produto depender de artefatos exploratórios que não
serão evoluídos.

## Decisão

O diretório `notebooks/` e o `requirements.txt` da raiz ficam preservados somente como histórico da
POC. Eles não fazem parte do produto, do build, das imagens, do lint, dos testes, da CI, das métricas
vigentes nem dos critérios de aceite das próximas fases.

Novos experimentos reproduzíveis devem ser implementados como código e fixtures versionadas no
componente responsável, com execução automatizada pelos targets Docker. Resultados históricos dos
notebooks não serão reutilizados como evidência sem uma reprodução independente no pipeline atual.

## Consequências

- O Ruff exclui `notebooks/`, e a automação não instala as dependências da raiz.
- Não serão corrigidos, migrados ou reexecutados notebooks durante a recuperação.
- Os arquivos permanecem no Git para consulta histórica; exclusão definitiva pode ser decidida
  separadamente, sem bloquear o produto.
