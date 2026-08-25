# TCC — QA Method SNPG

Projeto de TCC da UFSC: método de avaliação de qualidade para o Sistema Nacional de
Pós-Graduação (SNPG). O repositório contém notebooks de análise, um serviço FastAPI
(`qa-services/`) que implementa o método via RAG, e uma interface React (`qa-application/`).

## Estrutura principal

- `notebooks/`: análises exploratórias e validações estatísticas.
- `qa-services/`: API FastAPI com RAG (Qdrant) e integrações com LLMs.
  - `app/core/`: configurações e dependências.
  - `app/routers/`: endpoints HTTP.
  - `app/services/`: lógica de domínio e integrações.
- `qa-application/`: interface React (Create React App + Tailwind).
- `data/`: dados brutos e processados — nunca versionados se sensíveis.
- `requirements.txt`: dependências raiz (notebooks e ferramentas).

## Documentação canônica

- `docs/architecture/fundamental-concepts.md`: escopo, componentes e limites do sistema.
- `docs/architecture/evaluation-pipeline.md`: fluxo ponta a ponta de um documento.
- `docs/architecture/rag-pipeline.md`: indexação, recuperação e geração com Qdrant.
- `docs/operations/local-setup.md`: ambiente, variáveis e comandos.
- `docs/quality/evaluation-method.md`: dimensões, rubrica e prompt do avaliador.
- `docs/quality/rag-validation.md`: métricas de recuperação e experimentos.
- `docs/decisions/evaluator-llm-selection.md`: critérios e alternativas consideradas.

## Desenvolvimento

### Ambiente local

```bash
# Criar e ativar ambiente virtual
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Serviço FastAPI
cd qa-services
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Interface React
cd qa-application
npm install
npm start
```

### Qualidade e testes

```bash
# Lint (raiz)
ruff check .

# Lint (qa-services)
cd qa-services && ruff check .

# Testes
pytest
```

- Executar ruff e testes relevantes após mudanças Python.
- Nunca afirmar que uma validação passou sem executar o comando com sucesso.

## Convenções de implementação

- Menor alteração completa; preservar mudanças locais não relacionadas.
- Seguir Ruff com regras `E`, `W` e `F`.
- Nomes explícitos, retornos antecipados, type hints.
- Regra de negócio fora de prompts e clientes de infraestrutura.
- Não adicionar dependência quando a stdlib ou dependência existente resolver.

## Spec-driven e system design

- Use o fluxo em `docs/processes/spec-driven-development.md` para funcionalidades ou mudanças
  que alterem comportamento observável, contratos, dados ou mais de um componente.
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
