# Encontrar trabalhos e evidências no acervo

- **Status:** `validado`
- **Responsável:** mantenedor do projeto
- **Última atualização:** 2026-11-21
- **System design:** [Acervo acadêmico](../architecture/academic-catalog-design.md)
- **Decisão:** [Continuidade do Question Answering](../decisions/restore-question-answering-focus.md)

## Objetivo e demonstração

Uma pessoa que explora a produção de um PPG consegue admitir dois PDFs autorizados, catalogá-los
com metadados acadêmicos e encontrar evidências entre os trabalhos combinando assunto, ano, área
e orientação. Cada trecho abre o texto extraído da página correta e identifica sua revisão.
O fluxo começa em `/collection` e dispensa avaliação individual, credenciais e inferência externa.

## Escopo

Inclui upload pelo contrato existente, cadastro manual, edição com controle de concorrência,
listagem paginada, filtros, busca lexical entre documentos e abertura de evidência textual.
Contratos e dados seguem o system design. Exclui síntese, vetorial entre documentos, OCR, coleta
automática, dashboard temático nacional, cobrança, autenticação e multitenancy.

## Requisitos e aceite

- **REQ-001 / AC-001:** cadastrar um PDF diretamente no acervo e informar título, tipo, ano,
  instituição, PPG, área, autor e orientação; metadados ausentes continuam nulos e sua origem é
  explicitamente manual. Upload não dispara avaliação nem chamada de provedor.
- **REQ-002 / AC-002:** persistir e reabrir os metadados; atualização com revisão antiga retorna
  conflito sem sobrescrever a edição mais recente. PDFs existentes podem ser catalogados.
- **REQ-003 / AC-003:** listar e paginar somente trabalhos catalogados; filtros combinados de
  tipo, período e campos textuais incluem e excluem corretamente; contagens são do conjunto
  filtrado e campos desconhecidos não passam em filtros preenchidos.
- **REQ-004 / AC-004:** assunto comum a dois trabalhos recupera evidências dos dois. Filtros são
  aplicados antes do ranking, empates são estáveis e consulta sem correspondência retorna vazio.
- **REQ-005 / AC-005:** cada resultado identifica documento, SHA256, revisão dos metadados,
  unidade e página; abrir evidência recupera o texto da unidade correta. Unidade de outro
  documento não pode ser apresentada como fonte do documento selecionado.
- **REQ-006 / AC-006:** erros, carregamento, vazio e conflito são visíveis na interface;
  corpos inválidos, limites excessivos, campos extras e anos invertidos são rejeitados.
- **REQ-007 / AC-007:** contratos atuais por documento, avaliação, insights e judge continuam
  operacionais. Nenhuma inferência externa é necessária para catalogar ou pesquisar.

## Plano de implementação

1. [x] Registrar desenho, contratos e ordem das próximas entregas (REQ-001–007).
2. [x] Migração aditiva, schemas, persistência e rotas do catálogo (REQ-001–006).
3. [x] Tela Acervo com admissão, edição, filtros e abertura de evidência (REQ-001–006).
4. [x] Testes, smoke e reconciliação da documentação (REQ-001–007).

## Plano de validação

| Critério | Evidência executada em 2026-11-21 | Resultado |
|---|---|---|
| AC-001, AC-002 | `test_catalog_api.py`, `test_postgres_catalog.py`, `Collection.test.tsx`: cadastro, reabertura, duas escritas concorrentes e criação concorrente | aprovado |
| AC-003, AC-004 | PostgreSQL: corpus sintético com quatro PDFs, um não catalogado; filtros combinados, ano desconhecido, totais, paginação estável e offset além do fim | aprovado |
| AC-005 | API/PostgreSQL, interface e smoke: abertura da unidade correta, rejeição de fonte cruzada e SHA/página preservados | aprovado |
| AC-006 | API e interface: campos inválidos, erros, vazios, conflito e corrida entre upload e listagem inicial | aprovado |
| AC-007 | Backend completo: 139 testes; frontend completo: 25 testes; Ruff, typecheck, ESLint, build e smoke HTTP com API/worker/Vite/PostgreSQL | aprovado no host |

Os 28 testes novos do backend e os oito da interface integram automaticamente os targets Docker
existentes. O smoke versionado em `scripts/compose_smoke.py` agora cobre também o acervo.

Comandos executados, após instalar as dependências fixadas sem alterar manifests ou locks:

```bash
# qa-services; DATABASE_URL apontou exclusivamente para o banco de teste temporário
PYTHON_DOTENV_DISABLED=1 /tmp/qa-implementation/venv/bin/ruff check --no-cache app tests
DATABASE_URL=postgresql://qa_catalog@127.0.0.1:55432/qa_catalog_test \
  PYTHON_DOTENV_DISABLED=1 /tmp/qa-implementation/venv/bin/pytest -p no:cacheprovider -m 'not live'

# qa-application
npm run typecheck
npm run lint
npm run test:run
npm run build

# raiz, com API, worker e Vite iniciados contra o banco temporário
QA_API_URL=http://127.0.0.1:8000 QA_WEB_URL=http://127.0.0.1:5173 \
  PYTHON_DOTENV_DISABLED=1 /tmp/qa-implementation/venv/bin/python scripts/compose_smoke.py
```

### Limitações da validação

- Docker Desktop não está integrado nesta distribuição WSL. Não foi executado o comando
  `./scripts/test-containers.sh`, nem repetido o teste containerizado de backup/restore.
- O banco temporário usou PostgreSQL 18.6/pgvector 0.8.1, diferente do Compose (17/0.8.6).
  A suíte completa passou nessa combinação; isso não substitui a execução da imagem de CI.
- Python 3.12.14 corresponde ao manifesto. Node 24.22.1 satisfaz o intervalo do package.json,
  mas difere do 24.20.0 fixado no manifesto e Dockerfile.
- Playwright MCP não iniciou: Chrome ausente em `/opt/google/chrome/chrome`; sua instalação
  exigiu root e foi bloqueada. A verificação visual foi executada com Playwright e Chromium 159
  portáteis, sem instalação de sistema: upload/cadastro de dois PDFs, busca, filtro, abertura
  da fonte e viewport mobile 390 × 844 sem overflow horizontal passaram, sem `pageerror`.
  As [capturas e evidências](../evidence/academic-catalog/README.md) registram a execução.
- Fixtures e testes de contrato não medem a utilidade acadêmica nem a qualidade de recuperação
  em um corpus real do PPGEGC. Nenhum provedor externo foi chamado.

## Questões abertas e desvios

Nenhuma decisão bloqueante. Nenhum desvio de escopo.
