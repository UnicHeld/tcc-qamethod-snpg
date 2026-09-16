# Configuração local

## Pré-requisitos

- Docker Engine com Compose v2 para o caminho recomendado; ou
- mise 2026.9 ou compatível;
- Python 3.12.14 e uv 0.12.10, instalados pelo manifesto do serviço;
- Node.js 24.20.0 e npm 11, instalados pelo manifesto da interface.

Pesos de embedding, OpenAI, OCR e credenciais externas não são necessários para abrir o perfil
padrão. O PostgreSQL local inclui pgvector, mas a capacidade vetorial permanece desabilitada e não
baixa modelo até o operador selecionar o perfil EV-02. A busca lexical usa somente o índice textual.

## Execução recomendada com Compose

Na raiz do repositório, construa e inicie API e interface:

```bash
docker compose up --build
```

A interface abre em `http://127.0.0.1:5173`; a API permanece acessível diretamente em
`http://127.0.0.1:8000`. A interface usa o proxy local `/api`, sem expor o hostname interno do
contêiner ao navegador. Encerre com `Ctrl+C` e remova os serviços com `docker compose down`.

O volume `qa-method_postgres_data` preserva documentos e resultados entre reinícios e também após
`docker compose down`. Não use `docker compose down --volumes` com dados úteis: essa opção apaga o
banco local. O PostgreSQL não publica porta no host; a API é sua fronteira de acesso normal.

A classificação conservadora da extração por página fica disponível em
`GET /api/v1/documents/{document_id}/pages`. `ocr_candidate` apenas indica imagem raster sem texto
extraído; o perfil padrão não instala nem executa OCR.

A rota `POST /api/v1/search` pesquisa apenas as unidades do documento informado e devolve trechos
com página e origem. Ela funciona no perfil padrão, não usa LLM ou embedding e está disponível na
tela `http://127.0.0.1:5173/search` após ao menos um documento ser admitido.

Para habilitar recuperação semântica local, inicie com o overlay opt-in:

```bash
docker compose -f compose.yaml -f compose.vector.yaml up --build
```

O primeiro uso baixa `intfloat/multilingual-e5-small` para o volume `embedding_cache`; os próximos
usos reutilizam cache e índice por revisão. A resposta e a tela identificam modelo, 384 dimensões e
versão de chunk. Uma falha vetorial é explícita e não substitui silenciosamente o resultado por
busca lexical. Para o smoke sintético reproduzível, que exige rede apenas para baixar o modelo:

```bash
QA_VECTOR_TEST_CONFIRM=download-local-model ./scripts/test-vector-search-live.sh
```

A tela `http://127.0.0.1:5173/insights` cria uma pergunta única e persistente. O worker recupera
até cinco evidências, congela página/unidade/trecho e então produz uma resposta demo ou real com
citações validadas. O modo real envia ao provedor somente a pergunta e os trechos recuperados após
confirmação explícita; não envia o PDF completo por esse fluxo.

Para desenvolver com hot reload e diretórios de código montados somente para leitura:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Mudanças em dependências ou manifests exigem novo `--build`.

## Backup e restauração local

Com a stack Compose iniciada, crie um dump PostgreSQL customizado em um diretório seguro fora do
repositório:

```bash
./scripts/backup-postgres.sh /caminho/seguro/qa-method.dump
```

O script grava primeiro um arquivo temporário no mesmo diretório, aplica permissão `600` e só então
faz a troca atômica. Ele recusa substituir um backup existente; para uma substituição consciente,
defina `QA_BACKUP_OVERWRITE=1` apenas naquela execução.

Restaurar substitui o estado atual do banco, interrompe temporariamente API/worker e não pode ser
desfeito sem outro backup. Confira o arquivo e execute com a frase explícita:

```bash
QA_RESTORE_CONFIRM=restore-local-database \
  ./scripts/restore-postgres.sh /caminho/seguro/qa-method.dump
```

O restore usa uma única transação e reinicia API/worker ao terminar. Runs que estavam `running` no
backup são reconciliados como `interrupted`; nenhuma chamada de provedor é retomada automaticamente.
`./scripts/test-containers.sh` ensaia backup, remoção e restore somente no volume descartável do
projeto de teste e nunca no volume padrão da aplicação.

## Testes automatizados em contêineres

Execute toda a qualidade offline com um comando:

```bash
./scripts/test-containers.sh
```

O script usa um projeto Compose isolado, valida a configuração, constrói as imagens, executa Ruff,
pytest, typecheck, ESLint, Vitest e build Vite, inicia a stack, roda o smoke HTTP e remove os
serviços ao final. As suítes executam sem rede e com chaves vazias. O workflow
`.github/workflows/container-quality.yml` chama o mesmo script em pushes para `main` e pull requests.

## Execução alternativa no host

## Serviço FastAPI

O serviço possui ambiente independente das bibliotecas de notebooks da raiz:

```bash
cd qa-services
mise install
mise exec -- uv sync --group dev
mise exec -- uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Nesse modo, a avaliação provisória continua disponível sem banco. Os endpoints persistentes
`/api/v1/documents`, `/api/v1/runs`, `/api/v1/search` e `/api/v1/insights` exigem `DATABASE_URL` apontando para um
PostgreSQL acessível pelo host e o comando `mise exec -- uv run python -m app.core.migrations` antes
do Uvicorn. Execute também `mise exec -- uv run python -m app.worker` em outro terminal para
processar a fila. O caminho recomendado para a stack persistente continua sendo o Compose.

Verificações sem rede nem credenciais:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/capabilities
```

O perfil `demo` é o padrão e produz resultado determinístico marcado como “Simulado — sem
inferência LLM”. A liveness não inicializa nem chama o Google Gemini.

## Interface React

Em outro terminal:

```bash
cd qa-application
mise install
mise exec -- npm ci
mise exec -- npm run dev
```

Acesso: `http://127.0.0.1:5173`. A API permite, por padrão, apenas as origens locais
`http://127.0.0.1:5173` e `http://localhost:5173`.

## Inferência real opt-in

O modo real usa o SDK `google-genai` e só fica disponível quando o backend encontra uma chave e o
modelo configurado está na allowlist. Antes de cada teste, confira no console do provedor a quota,
o plano de faturamento e a autorização do documento. A aplicação não garante gratuidade da conta.

Variáveis reconhecidas pelo backend:

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | PostgreSQL local do Compose | Conexão do backend; nunca enviar ao frontend |
| `GEMINI_API_KEY` ou `GOOGLE_API_KEY` | ausente | Credencial do Gemini; nunca enviar ao frontend |
| `GEMINI_FALLBACK_API_KEY` | ausente | Reserva de outro projeto gratuito; usada uma vez somente após erro de quota da principal |
| `QA_DEFAULT_MODE` | `demo` | `demo` ou `real`; volta a `demo` se o modo real estiver indisponível |
| `QA_GEMINI_MODEL` | `gemini-3.5-flash-lite` | Modelo estável solicitado no modo real |
| `QA_JUDGE_GEMINI_MODEL` | ausente | Segundo modelo usado pelo judge real; deve diferir do avaliador |
| `QA_ALLOWED_GEMINI_MODELS` | modelo padrão | Allowlist separada por vírgulas, sem fallback automático |
| `QA_MAX_UPLOAD_BYTES` | `20971520` | Limite total do upload |
| `QA_MAX_PAGES` | `300` | Limite de páginas por PDF |
| `QA_PARSE_TIMEOUT_SECONDS` | `60` | Timeout da extração |
| `QA_LLM_TIMEOUT_SECONDS` | `180` | Timeout do provedor |
| `QA_VECTOR_SEARCH_ENABLED` | `false` | Habilita busca/insight vetorial local de forma opt-in |
| `QA_EMBEDDING_MODEL` | `intfloat/multilingual-e5-small` | Modelo local do perfil vetorial |
| `QA_EMBEDDING_CACHE_DIR` | ausente | Cache persistente dos pesos locais |
| `QA_CORS_ORIGINS` | origens Vite locais | Origens explícitas separadas por vírgulas |

A interface aceita `VITE_API_BASE_URL` para apontar a outra URL local. Não use prefixo `VITE_`
para chaves: essas variáveis entram no bundle público.

Para executar uma avaliação real, selecione o modo na tela e confirme explicitamente o envio do
texto extraído. Se uma reserva estiver configurada, um erro de quota da principal autoriza um único
reenvio pela reserva. Outros erros encerram a execução; não há troca de modelo, plano pago ou
substituição silenciosa por simulação. O resultado identifica apenas `primary` ou `fallback`.

Para executar o judge real, configure `QA_JUDGE_GEMINI_MODEL` com outro modelo e inclua tanto ele
quanto `QA_GEMINI_MODEL` em `QA_ALLOWED_GEMINI_MODELS`. A tela exige novo consentimento. O judge
envia ao provedor o parecer congelado e somente os trechos que esse parecer citou; não reenvia o PDF
nem recupera evidências adicionais. O modo demo continua disponível sem chave e sem rede.

O padrão `gemini-3.5-flash-lite` foi confirmado no catálogo em 2026-09-13. Um `404` do provedor
indica que o modelo configurado não está disponível para aquela chave/API; o backend não tenta a
reserva nesse caso, pois ela existe exclusivamente para esgotamento de quota.

## Validação da F1

```bash
cd qa-services
mise exec -- uv run ruff check app tests
mise exec -- uv run pytest -m "not live"
```

```bash
cd qa-application
mise exec -- npm run typecheck
mise exec -- npm run lint
mise exec -- npm run test:run
mise exec -- npm run build
```

A suíte `live` de provedores externos não roda por padrão. Comparação e backup/restauração estão
disponíveis na F3d; a busca vetorial opt-in pertence ao EV-02 e OCR ao EV-04 do
[roteiro de recuperação](../specs/prototype-recovery.md).

Para validar a fatia completa, incluindo contratos HTTP, walkthrough visual, responsividade,
teclado e o teste real opt-in, siga o
[roteiro passo a passo](prototype-recovery-test-plan.md). O estado consolidado das entregas está no
[checklist da recuperação](prototype-recovery-checklist.md).
