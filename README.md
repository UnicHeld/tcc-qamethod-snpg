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
- [Pipeline RAG](./docs/architecture/rag-pipeline.md): indexação, recuperação e geração com Qdrant.

## Operação

- [Configuração local](./docs/operations/local-setup.md): ambiente virtual, variáveis e execução.

## Qualidade

- [Método de avaliação](./docs/quality/evaluation-method.md): dimensões, rubrica e prompt do avaliador.
- [Validação RAG](./docs/quality/rag-validation.md): métricas de recuperação e experimentos de avaliação.

## Decisões

- [Escolha do LLM avaliador](./docs/decisions/evaluator-llm-selection.md): critérios e alternativas consideradas.

## Processos

- [Desenvolvimento](./docs/processes/development.md): fluxo de branches, commits e PR.
- [Spec-driven e system design](./docs/processes/spec-driven-development.md): gates, artefatos e rastreabilidade.

## Especificações

- [Índice e convenções](./docs/specs/README.md): ciclo de vida e nomenclatura das especificações.

## Regra de ownership documental

Cada fato deve possuir uma fonte principal. Quando um assunto precisar aparecer em outra
categoria, use resumo curto com link para a fonte principal.
