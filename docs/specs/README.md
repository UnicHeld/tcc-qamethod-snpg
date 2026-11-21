# Especificações

Esta pasta contém contratos verificáveis para mudanças de comportamento do TCC QA Method SNPG.
Use nomes em inglês e `kebab-case`, com um arquivo por mudança: `<slug>.md`.

Comece por `spec-template.md` e siga o processo em
`docs/processes/spec-driven-development.md`. Especificações substituídas permanecem no histórico e
devem apontar para a sucessora.

## Direção vigente

A [ADR de continuidade do Question Answering](../decisions/restore-question-answering-focus.md)
prioriza consulta ao acervo e síntese entre trabalhos usando a infraestrutura pós-TCC.
As especificações de recuperação conservam seus contratos e evidências. A primeira ampliação
para uma coleção está no acervo acadêmico; as próximas entregas seguem a sequência de evolução
e precisam de system design e especificações próprios antes da implementação.

## Índice

- [Evolução do produto](product-evolution.md): entregáveis por valor, complexidade e dependências.
- [Encontrar trabalhos no acervo](academic-catalog.md): cadastro manual e recuperação lexical
  entre documentos com filtros acadêmicos e abertura de evidências.
- [Recuperação e evolução do protótipo](prototype-recovery.md): roteiro em implementação para
  recuperar a execução, testar recursos gratuitos e preparar a versão documental.
- [Insights RAG rastreáveis](rag-insights.md): pergunta única, pacote congelado de evidências,
  geração citável e exportação do EV-03.
- [Judge separado de pareceres](judge-runs.md): parecer e evidências congelados, achados
  rastreáveis e modos demo/real opt-in do EV-05.
