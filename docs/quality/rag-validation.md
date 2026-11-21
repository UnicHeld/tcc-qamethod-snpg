# Validação RAG

- Estado: baselines funcionais lexical EV-01 e vetorial EV-02 executados; EV-03 valida contratos de
  geração/citação offline, mas qualidade semântica ainda não foi medida.

## Objetivo

Medir a relevância da recuperação e a fundamentação, precisão e utilidade das respostas de
Question Answering. A [ADR de continuidade](../decisions/restore-question-answering-focus.md)
prioriza consultas e sínteses sobre o acervo para apoiar análises de PPGs.

O avaliador direto atual não usa RAG. Avaliar notas e justificativas nas seis dimensões ou os
achados do judge é uma tarefa separada, descrita na [rubrica do avaliador](evaluation-method.md).

## Evidência histórica

O [registro do TCC de 2024](../history/tcc-2024.md) descreve o experimento com 150 documentos do
PPGEGC, a divisão por área e a análise manual das respostas. Sua acurácia de
recuperação/classificação não é uma medida de correção geral das respostas nem das notas do
avaliador. Os resultados pertencem ao estudo e não foram reproduzidos no pipeline atual.

Os notebooks em `notebooks/rag-validation/` e `notebooks/statistic/` são preservados apenas como
registro exploratório. Eles não serão migrados, corrigidos ou reexecutados e seus resultados não
devem ser tratados como evidência da implementação atual.

## Métricas para a evolução do QA

As métricas abaixo orientam novos experimentos; não são resultados já medidos nem uma descrição
das métricas históricas do TCC:

- **Precision@K e Recall@K:** relevância dos trabalhos e trechos retornados, conforme referência anotada.
- **Respeito aos filtros:** inclusão e exclusão corretas por metadados acadêmicos.
- **Fundamentação e correção:** suporte das afirmações pelas fontes e validade das citações,
  com revisão humana; resolver um ID não basta para comprovar suporte semântico.
- **Utilidade da síntese:** capacidade de responder à pergunta e apoiar a análise do PPG,
  deixando claros os limites da amostra e os casos de insuficiência.

Conjuntos, protocolos e limiares devem ser definidos na especificação do entregável antes de
alegar qualidade medida. As baselines por documento abaixo continuam como evidência funcional.

## Conjunto de referência

Novos experimentos exigem corpus autorizado, documentos/revisões identificados e consultas
anotadas com filtros e evidências esperadas. A disponibilidade e a autorização da coleção
histórica não são presumidas por esta documentação. Dados locais podem usar `data/`, respeitando
as regras de não versionar material sensível ou com restrições de uso.

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
