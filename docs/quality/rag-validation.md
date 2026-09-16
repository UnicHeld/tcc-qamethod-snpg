# Validação RAG

- Estado: baselines funcionais lexical EV-01 e vetorial EV-02 executados; EV-03 valida contratos de
  geração/citação offline, mas qualidade semântica ainda não foi medida.

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

O baseline EV-02 possui uma consulta sintética anotada com Recall@1 igual a 1,0; isso comprova
integração e recuperabilidade, não generalização. Métricas amplas ainda exigem corpus autorizado,
várias consultas anotadas e revisão humana.

No EV-03, testes verificam que a geração recebe apenas o pacote congelado, que toda citação resolve
para `E1..En` e que zero hits ou citação inexistente não publicam resposta. Ainda faltam avaliação
humana de fundamentação, precisão das respostas e comparação controlada com leitura direta.
