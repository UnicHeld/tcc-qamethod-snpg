# Pós-TCC — recuperação e evolução em 2026

- Natureza: registro da evolução posterior ao [TCC de 2024](tcc-2024.md).
- Conferência documental e do código: 2026-11-20.
- Snapshot de código consultado: `aedff05`, de 2026-09-16.
- As evidências de execução citadas permanecem datadas nos documentos originais; esta revisão
  não reexecutou a aplicação nem os experimentos do TCC.

## Linha do tempo no Git

| Data | Referência | Marco |
|---|---|---|
| 2024-11-14 | `ee766b1` | Último commit de 2024; inclui o protótipo e a avaliação direta |
| 2026-08-24 | `11568aa` | Início da retomada registrada, com organização documental |
| 2026-09-10 | `c35ea49`, `8523c88` | Recuperação da avaliação offline/real e migração da interface para Vite |
| 2026-09-15 | `c9cdd27` | Persistência, worker, histórico e busca de evidências |
| 2026-09-16 | `b5a360a` | Busca vetorial e insights RAG rastreáveis |
| 2026-09-16 | `8f14b49` | Judge separado de pareceres |
| 2026-11-20 | Revisão documental, sem novo código de produto | Separação dos períodos e decisão de continuidade do Question Answering |

Há aproximadamente um ano e nove meses sem commits registrados entre novembro de 2024 e
agosto de 2026. Isso descreve o histórico disponível, não comprova ausência de trabalho fora do Git.

## O que a retomada acrescentou

A recuperação tomou como ponto de partida o fluxo web de avaliação direta que já existia.
Os incrementos de 2026 incluem:

- Ambiente e dependências isolados, Compose, testes offline e CI.
- Adaptador Gemini atualizado, modo demo identificado, consentimento e erros explícitos.
- Unidades por página, revisão por hash, parecer estruturado e validação de evidências.
- PostgreSQL, filas, worker, histórico, reexecução, comparação e exportações.
- Busca lexical e busca vetorial opcional com embeddings locais e pgvector.
- Insights com pacote congelado de evidências e citações verificadas.
- Judge separado sobre pareceres e seus trechos citados.

Os contratos e limites vigentes estão nos [conceitos fundamentais](../architecture/fundamental-concepts.md),
no [pipeline RAG](../architecture/rag-pipeline.md) e nas respectivas especificações.
O [checklist da recuperação](../operations/prototype-recovery-checklist.md) conserva as evidências
e pendências de cada entrega.

## Diferença de rumo em relação ao trabalho acadêmico

A documentação introduzida em agosto de 2026 passou a descrever o projeto como avaliação de
qualidade em seis dimensões. O desenho posterior priorizou um laboratório local de análise
documental, pareceres e judge. Essa escolha organizou uma parte existente do código, mas
reduziu a centralidade da consulta estratégica a uma coleção descrita no TCC.

| Capacidade central no TCC | Situação no código pós-TCC consultado |
|---|---|
| Recuperar trabalhos de uma coleção | Busca lexical/vetorial restrita às unidades de um `document_id` |
| Filtrar por ano, área, autor e orientação | Os contratos ativos de busca/insights não possuem esses filtros acadêmicos |
| Sintetizar diferentes trabalhos em uma resposta | Insights recuperam contexto de um documento selecionado |
| Extrair metadados acadêmicos para consulta | O contrato persistido básico registra arquivo, hash e dados de extração; não cobre o catálogo acadêmico do TCC |
| Avaliar recuperação no corpus do PPGEGC | Testes e baselines novos não reproduzem o experimento com 150 documentos |
| Avaliação individual como serviço possível | Pareceres e judge receberam fluxos próprios e destaque na retomada |

O código legado de Qdrant/OpenAI permanece no repositório, mas não participa do pipeline ativo.
Guardar vários documentos no PostgreSQL não equivale a consultar ou sintetizar o acervo inteiro.

## O que permanece válido e o que muda de prioridade

A infraestrutura pós-TCC é a base para continuar o método original. A
[ADR de continuidade do Question Answering](../decisions/restore-question-answering-focus.md)
define o foco em perguntas sobre o acervo, com avaliação individual e judge como capacidades
complementares. Ela não exige restaurar versões antigas de modelos, Qdrant ou notebooks.

As especificações de recuperação, insights e judge continuam descrevendo as fatias implementadas
e suas pendências. Seus limites por documento não se tornam suporte a coleções por esta decisão.
Novos contratos para o acervo exigem system design, especificação e validação próprios.

## Continuidade funcional em 2026-11-21

Após a fotografia de setembro descrita acima, foi implementado o
[acervo acadêmico consultável](../specs/academic-catalog.md): cadastro manual de metadados,
filtros e busca lexical entre trabalhos com abertura da evidência textual. A tabela comparativa
anterior descreve o snapshot `aedff05`, não esta ampliação. Síntese entre documentos, coleta
automática e operação SaaS continuam planejadas na [evolução do produto](../specs/product-evolution.md).
