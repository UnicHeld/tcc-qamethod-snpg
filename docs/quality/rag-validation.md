# Validação RAG

- Estado: baseline lexical EV-01 implementado; métricas de recuperação semântica e de geração ainda
  não reproduzidas no pipeline atual.

## Objetivo

Medir a contribuição do pipeline RAG na qualidade das avaliações geradas, comparando
resultados com e sem recuperação de contexto.

## Evidência histórica

Os notebooks em `notebooks/rag-validation/` e `notebooks/statistic/` são preservados apenas como
registro exploratório. Eles não serão migrados, corrigidos ou reexecutados e seus resultados não
devem ser tratados como evidência da implementação atual.

Métricas utilizadas:
- **Precision@K** — fração de chunks recuperados que são relevantes.
- **Recall@K** — fração de chunks relevantes que foram recuperados.
- **Coerência da avaliação** — consistência entre avaliações de um mesmo documento.

## Conjunto de referência

Os documentos de referência usados para indexação e validação estão em `data/`.
Não versionar documentos com dados pessoais ou restrições de uso.

## Validação atual e futura

O EV-01 valida com fixture sintética que uma consulta lexical recupera a unidade esperada dentro do
documento correto, com página e ID determinísticos. Isso comprova o contrato funcional, não a
qualidade geral de relevância.

No EV-02, métricas como Precision@K e Recall@K serão recriadas em código versionado, com corpus
autorizado, fixtures anotadas e execução automatizada pelos targets Docker. Alterações de K,
métrica, embedding ou chunk serão comparadas por esse pipeline, sem depender dos notebooks
históricos.
