# Documentação — TCC QA Method SNPG

Os arquivos usam nomes em inglês, minúsculos e em `kebab-case`. `README.md` é reservado para
índices.

## TCC e pós-TCC

QA significa **Question Answering**. A direção do projeto é responder perguntas sobre um acervo
de teses e dissertações para apoiar análises de PPGs, aproveitando a infraestrutura pós-TCC.

- [TCC de 2024](./docs/history/tcc-2024.md): objetivo acadêmico, seis etapas e resultados do estudo.
- [Pós-TCC em 2026](./docs/history/post-tcc-2026.md): implementações, mudança de foco e limites atuais.
- [ADR de continuidade do Question Answering](./docs/decisions/restore-question-answering-focus.md):
  decisão vigente; avaliação individual e judge são serviços complementares.

O [acervo consultável](./docs/specs/academic-catalog.md) permite cadastrar metadados acadêmicos,
filtrar trabalhos e buscar evidências textuais entre documentos na tela `/collection`.
Busca vetorial e insights existentes continuam por documento; síntese entre trabalhos permanece
planejada. A [sequência de evolução do produto](./docs/specs/product-evolution.md) organiza as
próximas entregas até ingestão automática, operação SaaS e cobertura nacional.

## Categorias

| Categoria | Escopo | Não deve conter |
|---|---|---|
| [`history/`](./docs/history/) | TCC de 2024 e evolução pós-TCC | contratos vigentes ou capacidades futuras apresentadas como entregues |
| [`architecture/`](./docs/architecture/) | pipeline RAG, fluxo de avaliação, contratos de API | runbooks ou status |
| [`operations/`](./docs/operations/) | configuração local, variáveis de ambiente, execução dos serviços | decisões de design |
| [`quality/`](./docs/quality/) | rubrica do avaliador, métricas e validação de recuperação e respostas QA | arquitetura do runtime |
| [`decisions/`](./docs/decisions/) | alternativas avaliadas e decisões técnicas vigentes | instruções operacionais |
| [`specs/`](./docs/specs/) | requisitos, escopo e critérios de aceite de mudanças | decisões arquiteturais sem referência |
| [`processes/`](./docs/processes/) | processo de desenvolvimento e contribuição | arquitetura do produto |

## Arquitetura canônica

- [Acervo acadêmico](./docs/architecture/academic-catalog-design.md): cadastro manual, filtros,
  paginação e busca lexical entre documentos com fontes verificáveis.
- [Conceitos fundamentais](./docs/architecture/fundamental-concepts.md): escopo, componentes e responsabilidades.
- [Pipeline de avaliação](./docs/architecture/evaluation-pipeline.md): fluxo ponta a ponta de um documento.
- [Pipeline RAG](./docs/architecture/rag-pipeline.md): indexação, recuperação e geração com
  PostgreSQL + pgvector.
- [Insights RAG](./docs/architecture/rag-insights-design.md): pacote congelado, fila, geração
  citável e limites do EV-03.
- [Judge separado](./docs/architecture/judge-runs-design.md): segundo modelo opt-in sobre parecer e
  evidências congeladas, com fila e achados rastreáveis do EV-05.

## Desenhos propostos

- [Recuperação do protótipo](./docs/architecture/prototype-recovery-design.md): desenho pós-TCC
  parcialmente implementado; preserva contexto e limites das entregas de recuperação.

## Operação

- [Configuração local](./docs/operations/local-setup.md): ambiente virtual, variáveis e execução.
- [Checklist da recuperação](./docs/operations/prototype-recovery-checklist.md): entregas concluídas,
  itens parciais e próximos entregáveis de valor.
- [Roteiro de testes da recuperação](./docs/operations/prototype-recovery-test-plan.md): validação
  reproduzível do backend, frontend, API e walkthrough manual.

## Qualidade

- [Método de avaliação](./docs/quality/evaluation-method.md): rubrica do serviço complementar de
  avaliação individual.
- [Validação RAG](./docs/quality/rag-validation.md): evidência histórica, baselines atuais e
  avaliação futura da recuperação e das respostas de QA.

## Decisões

- [Continuidade do Question Answering](./docs/decisions/restore-question-answering-focus.md):
  preservar o objetivo do TCC usando as implementações pós-TCC.
- [Notebooks históricos da POC](./docs/decisions/archive-poc-notebooks.md): preservados para
  consulta, mas excluídos do produto, build, lint, testes e métricas vigentes.
- [Execução e testes com Compose](./docs/decisions/containerized-development-and-testing.md):
  imagens, perfis, isolamento offline e reutilização do mesmo comando na CI.
- [Persistência PostgreSQL](./docs/decisions/postgresql-local-persistence.md): banco local,
  migrações e integração incremental do pgvector entregue no EV-02.
- [Recuperação vetorial local](./docs/decisions/local-vector-retrieval.md): FastEmbed, perfil E5,
  chunks versionados e isolamento do fallback lexical.
- [Failover Gemini](./docs/decisions/gemini-credential-failover.md): uso restrito da credencial
  reserva após esgotamento de quota da principal.
- [Escolha histórica do LLM avaliador](./docs/decisions/evaluator-llm-selection.md): registro da
  configuração antiga do avaliador direto; não é a configuração vigente nem a do QA do TCC.

## Processos

- [Desenvolvimento](./docs/processes/development.md): fluxo de branches, commits e PR.
- [Spec-driven e system design](./docs/processes/spec-driven-development.md): gates, artefatos e rastreabilidade.

## Especificações

- [Evolução do produto](./docs/specs/product-evolution.md): ordem de complexidade, resultados e limites.
- [Acervo consultável](./docs/specs/academic-catalog.md): requisitos, demonstração e validação.
- [Índice e convenções](./docs/specs/README.md): ciclo de vida e nomenclatura das especificações.
- [Roteiro de recuperação do protótipo](./docs/specs/prototype-recovery.md): fases, tarefas,
  critérios de aceite, interface do laboratório e preparação para registro de software.
- [Insights RAG rastreáveis](./docs/specs/rag-insights.md): contrato e aceite do EV-03.
- [Judge separado de pareceres](./docs/specs/judge-runs.md): contrato e aceite dos modos demo e real
  opt-in do EV-05.

## Regra de ownership documental

Cada fato deve possuir uma fonte principal. Quando um assunto precisar aparecer em outra
categoria, use resumo curto com link para a fonte principal.
