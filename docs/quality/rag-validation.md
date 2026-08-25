# Validação RAG

## Objetivo

Medir a contribuição do pipeline RAG na qualidade das avaliações geradas, comparando
resultados com e sem recuperação de contexto.

## Experimentos

Os notebooks de validação estão em `notebooks/rag-validation/`.

Métricas utilizadas:
- **Precision@K** — fração de chunks recuperados que são relevantes.
- **Recall@K** — fração de chunks relevantes que foram recuperados.
- **Coerência da avaliação** — consistência entre avaliações de um mesmo documento.

## Conjunto de referência

Os documentos de referência usados para indexação e validação estão em `data/`.
Não versionar documentos com dados pessoais ou restrições de uso.

## Interpretação dos resultados

Os resultados estatísticos estão em `notebooks/statistic/`. Antes de alterar parâmetros de
recuperação (K, métrica de distância, tamanho de chunk), re-executar os notebooks e comparar
com os resultados registrados em `notebooks/results/`.
