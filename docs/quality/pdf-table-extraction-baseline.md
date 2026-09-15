# Baseline experimental de extração de tabela PDF

- Status: validado offline em fixture sintética; não promovido ao fluxo de produção.
- Data da medição: 2026-09-15.
- Escopo: baseline experimental F4b de extração de tabelas em PDF.

## Objetivo e método

O experimento compara duas representações do mesmo PDF digital sintético sem substituir o parser
da aplicação:

- `pypdf` permanece como baseline de texto e é medido pela presença dos sete valores literais
  não vazios da referência;
- `pdfplumber` é o candidato tabular e é medido por exact match das oito células, incluindo seus
  localizadores de página, linha e coluna.

A fixture é gerada em memória por `tests/pdf_factory.py`. Ela contém uma tabela de uma página,
quatro linhas e duas colunas, com cabeçalho, texto, zero literal, travessão e uma célula vazia. O
teste não usa PDF binário versionado, dado real, rede, OCR ou LLM.

## Ambiente e resultado

O ambiente containerizado usa Python 3.12.14, `pypdf` 6.18.0 e `pdfplumber` 0.11.10, fixados nos
manifests do backend.

| Medida | Referência | Resultado |
|---|---:|---:|
| Cobertura literal do baseline `pypdf` | 7 valores | 7/7 (100%) |
| Exact match do candidato `pdfplumber` | 8 células | 8/8 (100%) |
| Estrutura localizada | página 1, tabela 1, 4 × 2 | match exato |
| Distinções críticas | `None`, `"0"` e `"—"` | preservadas |

Reprodução focal, a partir da raiz do repositório:

```bash
docker compose --profile test run --rm backend-tests \
  pytest -p no:cacheprovider tests/test_pdf_table_experiment.py
```

O comando agregado `./scripts/test-containers.sh` também inclui esse teste na suíte offline.

## Limitações e decisão

O resultado demonstra somente que o candidato recupera esta grade simples e determinística. Ele
não mede tabelas sem bordas, células mescladas, múltiplas páginas, ordem de leitura complexa,
documentos escaneados, coordenadas geométricas ou variação encontrada em documentos reais. Uma
fixture não sustenta declarar um vencedor universal nem estimar qualidade para o corpus do SNPG.

Por isso, `pdfplumber` permanece no grupo de desenvolvimento/teste e em `app/experiments/`. Nenhum
endpoint, worker, dado persistido ou imagem de runtime o importa. Uma eventual promoção requer uma
amostra autorizada maior, referência anotada antes da medição e critérios explícitos de qualidade,
tempo e consumo de memória.
