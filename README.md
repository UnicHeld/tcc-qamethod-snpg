# Documentação — TCC QA Method SNPG

Os arquivos usam nomes em inglês, minúsculos e em `kebab-case`. `README.md` é reservado para
índices.

## Categorias

| Categoria | Escopo | Não deve conter |
|---|---|---|
| [`architecture/`](./docs/architecture/) | pipeline RAG, fluxo de avaliação, contratos de API | runbooks ou status |
| [`operations/`](./docs/operations/) | configuração local, variáveis de ambiente, execução dos serviços | decisões de design |
| [`quality/`](./docs/quality/) | método de avaliação, dimensões, métricas e validação RAG | arquitetura do runtime |
| [`decisions/`](./docs/decisions/) | alternativas avaliadas e decisões técnicas vigentes | instruções operacionais |
| [`specs/`](./docs/specs/) | requisitos, escopo e critérios de aceite de mudanças | decisões arquiteturais sem referência |
| [`processes/`](./docs/processes/) | processo de desenvolvimento e contribuição | arquitetura do produto |

## Arquitetura canônica

- [Conceitos fundamentais](./docs/architecture/fundamental-concepts.md): escopo, componentes e responsabilidades.
- [Pipeline de avaliação](./docs/architecture/evaluation-pipeline.md): fluxo ponta a ponta de um documento.
- [Pipeline RAG](./docs/architecture/rag-pipeline.md): indexação, recuperação e geração com
  PostgreSQL + pgvector.
- [Insights RAG](./docs/architecture/rag-insights-design.md): pacote congelado, fila, geração
  citável e limites do EV-03.

## Desenhos propostos

- [Recuperação do protótipo](./docs/architecture/prototype-recovery-design.md): arquitetura alvo local,
  modular e sem SaaS; não descreve funcionalidades já implementadas.

## Operação

- [Configuração local](./docs/operations/local-setup.md): ambiente virtual, variáveis e execução.
- [Checklist da recuperação](./docs/operations/prototype-recovery-checklist.md): entregas concluídas,
  itens parciais e próximos entregáveis de valor.
- [Roteiro de testes da recuperação](./docs/operations/prototype-recovery-test-plan.md): validação
  reproduzível do backend, frontend, API e walkthrough manual.

## Qualidade

- [Método de avaliação](./docs/quality/evaluation-method.md): dimensões, rubrica e prompt do avaliador.
- [Validação RAG](./docs/quality/rag-validation.md): métricas de recuperação e experimentos de avaliação.

## Decisões

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
- [Escolha do LLM avaliador](./docs/decisions/evaluator-llm-selection.md): critérios e alternativas consideradas.

## Processos

- [Desenvolvimento](./docs/processes/development.md): fluxo de branches, commits e PR.
- [Spec-driven e system design](./docs/processes/spec-driven-development.md): gates, artefatos e rastreabilidade.

## Especificações

- [Índice e convenções](./docs/specs/README.md): ciclo de vida e nomenclatura das especificações.
- [Roteiro de recuperação do protótipo](./docs/specs/prototype-recovery.md): fases, tarefas,
  critérios de aceite, interface do laboratório e preparação para registro de software.
- [Insights RAG rastreáveis](./docs/specs/rag-insights.md): contrato e aceite do EV-03.

## Regra de ownership documental

Cada fato deve possuir uma fonte principal. Quando um assunto precisar aparecer em outra
categoria, use resumo curto com link para a fonte principal.
