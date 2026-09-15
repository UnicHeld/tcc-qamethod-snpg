# TCC — QA Method SNPG

Projeto de TCC da UFSC: método de avaliação de qualidade para o Sistema Nacional de
Pós-Graduação (SNPG). O repositório preserva notebooks históricos da POC, contém um serviço FastAPI
(`qa-services/`) que implementa avaliação direta e prepara RAG com PostgreSQL + pgvector, além de
uma interface React (`qa-application/`).

## Estrutura principal

- `notebooks/`: arquivo histórico da POC; fora do produto, build, lint, testes e escopo de evolução.
- `qa-services/`: API FastAPI com avaliação documental, persistência PostgreSQL, RAG planejado com
  pgvector e integrações com LLMs.
  - `app/core/`: configurações e dependências.
  - `app/routers/`: endpoints HTTP.
  - `app/services/`: lógica de domínio e integrações.
- `qa-application/`: interface React (Vite + Tailwind).
- `data/`: dados brutos e processados — nunca versionados se sensíveis.
- `requirements.txt`: dependências históricas da POC; não instalar para desenvolver o produto.

## Documentação canônica

- `docs/architecture/fundamental-concepts.md`: escopo, componentes e limites do sistema.
- `docs/architecture/evaluation-pipeline.md`: fluxo ponta a ponta de um documento.
- `docs/architecture/rag-pipeline.md`: indexação, recuperação e geração com PostgreSQL + pgvector.
- `docs/operations/local-setup.md`: ambiente, variáveis e comandos.
- `docs/quality/evaluation-method.md`: dimensões, rubrica e prompt do avaliador.
- `docs/quality/rag-validation.md`: métricas de recuperação e experimentos.
- `docs/decisions/evaluator-llm-selection.md`: critérios e alternativas consideradas.

## Desenvolvimento

### Ambiente local

```bash
# Stack completa, em modo estável
docker compose up --build

# Desenvolvimento com hot reload
docker compose -f compose.yaml -f compose.dev.yaml up --build

# Alternativa no host: consulte docs/operations/local-setup.md
```

### Qualidade e testes

```bash
# Lint, typecheck, testes backend/frontend, builds e smoke da stack
./scripts/test-containers.sh
```

- Manter dependências de runtime/desenvolvimento/teste nos targets Docker correspondentes.
- Toda nova feature precisa de testes offline relevantes executáveis pelo comando containerizado;
  testes reais de provedores permanecem opt-in e fora da CI comum.
- Não corrigir, migrar ou reexecutar `notebooks/`; novos experimentos devem ser código testável no
  componente responsável.
- Executar Ruff e testes relevantes após mudanças Python.
- Nunca afirmar que uma validação passou sem executar o comando com sucesso.

## Convenções de implementação

- Menor alteração completa; preservar mudanças locais não relacionadas.
- Seguir Ruff com regras `E`, `W` e `F`.
- Nomes explícitos, retornos antecipados, type hints.
- Regra de negócio fora de prompts e clientes de infraestrutura.
- Não adicionar dependência quando a stdlib ou dependência existente resolver.

## Eficiência de contexto e tokens

- Responder e reportar progresso de forma concisa; detalhar somente quando solicitado ou necessário
  para decisão, segurança ou diagnóstico.
- Ler primeiro os arquivos diretamente relacionados à tarefa. Consultar documentação canônica por
  demanda, sem carregar documentos ou diretórios inteiros preventivamente.
- Agrupar buscas e inspeções independentes e evitar reler conteúdo que não mudou.
- Executar primeiro as validações mínimas relevantes. Ampliar ou repetir testes somente após nova
  mudança, falha ou risco ainda não coberto.
- Não criar artefatos, planos, skills ou subagentes quando a tarefa puder ser concluída diretamente
  com a mesma qualidade.

## Spec-driven e system design

- Use o fluxo em `docs/processes/spec-driven-development.md` para funcionalidades ou mudanças
  que alterem comportamento observável, contratos, dados ou mais de um componente.
- Organize roadmap e próximos passos por entregáveis de valor: usuário/problema, resultado
  observável, demonstração ponta a ponta, critérios de aceite e limites explícitos.
- Migração, endpoint, biblioteca ou troca de infraestrutura são habilitadores técnicos dentro de
  um entregável; não devem ser apresentados isoladamente como valor concluído.
- Antes da especificação, produza system design quando houver decisão arquitetural, novo contrato
  entre componentes, persistência, integração externa ou trade-off relevante de segurança,
  confiabilidade, desempenho ou custo.
- Registre especificações em `docs/specs/` e mantenha requisitos e critérios de aceite rastreáveis.
- Registre arquitetura em `docs/architecture/`; decisões e alternativas descartadas pertencem a
  `docs/decisions/`.
- Correções locais e mudanças exclusivamente documentais podem dispensar novos artefatos. Declare
  essa decisão no plano ou na entrega.
- Não implemente uma especificação com decisões bloqueantes em aberto. Se o usuário já solicitou
  a implementação e não houver decisão bloqueante, a especificação pode seguir no mesmo fluxo.

## Git e entrega

- Inspecionar `git status` antes e depois de alterações substanciais.
- Não sobrescrever trabalho local não relacionado.
- Não fazer commit ou push sem pedido explícito.
- Usar Conventional Commits.

Ao concluir, informar arquivos alterados, validações executadas e riscos conhecidos.
