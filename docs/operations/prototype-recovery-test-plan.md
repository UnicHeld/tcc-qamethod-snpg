# Roteiro de testes da recuperação do protótipo

- Escopo: fluxo público F1/F2, recuperação F3a–F3d, extração F4a–F4c e buscas EV-01/EV-02
  containerizados.
- Perfil obrigatório: `demo`, offline e sem credenciais.
- Perfis opcionais: embedding local com download consciente; inferência real somente com autorização
  e quota verificadas.
- Fora do escopo: `notebooks/`, dependências da POC, OCR, geração RAG e judge.

Este roteiro indica o que executar, o resultado esperado e a evidência que deve ser registrada.
Não considere uma etapa aprovada sem observar o resultado descrito. Em caso de falha, preserve a
saída do comando e consulte a seção de diagnóstico antes de repetir.

Referências: [configuração local](local-setup.md),
[checklist da recuperação](prototype-recovery-checklist.md) e
[critérios de aceite](../specs/prototype-recovery.md).

## 1. Condições de segurança

Antes de começar:

1. Use somente o PDF sintético criado neste roteiro ou um documento público/autorizado.
2. Não coloque chaves em arquivos versionados, comandos, capturas de tela ou exportações.
3. Não instale o `requirements.txt` da raiz e não execute notebooks.
4. O teste real da seção 12 não faz parte da aprovação offline e deve permanecer desabilitado se
   plano, quota, cobrança ou autorização do documento não estiverem claros.

Para garantir o perfil offline nos testes manuais, use um terminal novo e retire eventuais chaves
somente dessa sessão:

```bash
unset GEMINI_API_KEY GOOGLE_API_KEY
```

Resultado esperado: o comando não imprime valores e as chamadas posteriores a `/capabilities`
informam que o modo real está indisponível.

## 2. Verificar os pré-requisitos

Na raiz do repositório:

```bash
docker --version
docker compose version
git status --short
git rev-parse --short HEAD
```

Resultado esperado:

- Docker e Compose respondem com suas versões, sem erro de daemon ou permissão;
- o Git informa o hash atual;
- `git status` pode listar mudanças locais, mas elas não devem ser apagadas para executar o teste.

Se Docker ou Compose falhar, interrompa o roteiro e corrija a instalação antes de continuar.

## 3. Executar toda a validação automatizada

Execute:

```bash
./scripts/test-containers.sh
```

O primeiro build pode demorar porque baixa imagens e dependências. O script cria o projeto Compose
isolado `qa-method-test` e remove seus serviços ao final.

Resultado esperado:

- configuração do Compose válida;
- imagens `api`, `web`, `worker`, `backend-tests` e `frontend-tests` construídas;
- Ruff: `All checks passed!`;
- pytest: `97 passed`; dois avisos de depreciação do TestClient são conhecidos e não reprovam;
- TypeScript e ESLint sem erros;
- Vitest: 4 arquivos e 15 testes aprovados;
- build Vite concluído;
- API, interface, worker e PostgreSQL iniciam durante o smoke;
- o smoke admite um documento, reabre a classificação `extracted`, recupera uma evidência lexical,
  valida um run de seis dimensões e um insight demo idempotente com pacote/citação congelados;
- o smoke operacional cria/restaura um backup e confirma `running → interrupted` após reinício;
- mensagem `Smoke test dos contêineres concluído com sucesso.`;
- nenhum teste de provedor real é executado e nenhuma chave é usada.

Qualquer exit code diferente de zero reprova esta etapa. Não avance como se a suíte tivesse passado.

## 4. Iniciar a aplicação para os testes manuais

Execute:

```bash
docker compose up --build --detach --wait
docker compose ps
```

Resultado esperado:

- `api` e `web` aparecem como `Up` e `healthy`; `worker` e `database` aparecem como `Up`;
- somente `127.0.0.1:8000` e `127.0.0.1:5173` são publicados no host;
- `backend-tests`, `frontend-tests` e `smoke-tests` não permanecem em execução.

## 5. Verificar API, proxy e rotas da interface

Execute:

```bash
curl --fail-with-body --silent --show-error http://127.0.0.1:8000/health
curl --fail-with-body --silent --show-error http://127.0.0.1:8000/capabilities
curl --fail-with-body --silent --show-error http://127.0.0.1:5173/api/health
curl --fail-with-body --silent --show-error --output /dev/null http://127.0.0.1:5173/
curl --fail-with-body --silent --show-error --output /dev/null http://127.0.0.1:5173/evaluation
curl --fail-with-body --silent --show-error --output /dev/null http://127.0.0.1:5173/search
```

Resultado esperado:

- todos os comandos terminam com exit code zero;
- `/health` retorna `status: "ok"`;
- o health direto e o acessado pelo proxy `/api` representam o mesmo serviço;
- `/capabilities` informa o modo `demo` disponível, com provedor `local` e modelo
  `deterministic-demo-v1`;
- sem chave configurada, o modo `real` aparece indisponível com uma explicação;
- a resposta nunca contém o valor de uma credencial;
- `/`, `/evaluation` e `/search` respondem HTTP 200, comprovando o fallback de rotas da SPA.

## 6. Criar a fixture PDF sintética

No mesmo terminal, crie um diretório temporário e gere o PDF usando o contêiner de testes:

```bash
QA_TEST_DIR="$(mktemp -d -t qa-method-test.XXXXXX)"
export QA_TEST_DIR
docker compose --profile test run --rm --no-deps -T \
  backend-tests \
  python -c 'import sys; from tests.pdf_factory import synthetic_pdf; sys.stdout.buffer.write(synthetic_pdf("Metodo QA para o SNPG"))' \
  > "$QA_TEST_DIR/demo.pdf"
ls -lh "$QA_TEST_DIR/demo.pdf"
```

Resultado esperado:

- o contêiner termina com exit code zero;
- `demo.pdf` existe no diretório temporário e possui tamanho maior que zero;
- nenhum arquivo é criado em `notebooks/`, `data/` ou no runtime da aplicação.

O PDF é enviado pela saída padrão do contêiner e gravado pelo seu próprio shell. Isso evita
diferenças de UID/GID em diretórios montados. Se aparecer `PermissionError: /fixtures/demo.pdf`,
você executou a versão antiga do comando com volume; use o bloco acima e não aplique `chmod 777`.

## 7. Testar a avaliação demo pela API

Faça duas chamadas iguais pelo proxy da interface:

```bash
curl --fail-with-body --silent --show-error \
  --request POST http://127.0.0.1:5173/api/evaluation/upload \
  --form "file=@$QA_TEST_DIR/demo.pdf;type=application/pdf" \
  --form 'mode=demo' \
  --form 'confirm_external_processing=false' \
  --output "$QA_TEST_DIR/demo-1.json"

curl --fail-with-body --silent --show-error \
  --request POST http://127.0.0.1:5173/api/evaluation/upload \
  --form "file=@$QA_TEST_DIR/demo.pdf;type=application/pdf" \
  --form 'mode=demo' \
  --form 'confirm_external_processing=false' \
  --output "$QA_TEST_DIR/demo-2.json"

docker compose exec -T api python -m json.tool < "$QA_TEST_DIR/demo-1.json"
cmp --silent "$QA_TEST_DIR/demo-1.json" "$QA_TEST_DIR/demo-2.json"
```

Resultado esperado:

- as duas chamadas respondem HTTP 200;
- `cmp` termina com exit code zero, comprovando resultado determinístico para a mesma fixture;
- `mode` é `demo` e `simulated` é `true`;
- `mode_label` é `Simulado — sem inferência LLM`;
- `provider` é `local` e `model` é `deterministic-demo-v1`;
- `document.sha256`, `page_count` e `character_count` estão preenchidos;
- `document.units` contém IDs no formato `<sha256>:page:<n>` e página física, sem expor texto;
- `report.revision_sha256` coincide com `document.sha256` e `report.simulated` é `true`;
- `report.dimensions` contém exatamente as seis dimensões, cada uma com nota 5.0 e referência a
  uma unidade existente;
- `result_markdown` contém exatamente as seis dimensões do método;
- o Markdown mostra as páginas de evidência e é coerente com os dados de `report`;
- não existe nota final agregada;
- `usage.kind` é `simulated`, sem tokens reais inventados.

## 8. Exercitar falhas seguras

Crie duas entradas inválidas:

```bash
: > "$QA_TEST_DIR/empty.pdf"
printf '%s\n' 'not a pdf' > "$QA_TEST_DIR/invalid.pdf"
```

### 8.1 Arquivo vazio

```bash
curl --silent --show-error --include \
  --request POST http://127.0.0.1:5173/api/evaluation/upload \
  --form "file=@$QA_TEST_DIR/empty.pdf;type=application/pdf" \
  --form 'mode=demo' \
  --form 'confirm_external_processing=false'
```

Resultado esperado: HTTP 400, `detail.code` igual a `empty_file` e nenhuma resposta de sucesso.

### 8.2 PDF inválido

```bash
curl --silent --show-error --include \
  --request POST http://127.0.0.1:5173/api/evaluation/upload \
  --form "file=@$QA_TEST_DIR/invalid.pdf;type=application/pdf" \
  --form 'mode=demo' \
  --form 'confirm_external_processing=false'
```

Resultado esperado: HTTP 422, `detail.code` igual a `invalid_pdf` e nenhuma resposta parcial.

### 8.3 Modo real sem consentimento

Esta chamada é segura porque o backend deve recusá-la antes de contatar qualquer provedor:

```bash
curl --silent --show-error --include \
  --request POST http://127.0.0.1:5173/api/evaluation/upload \
  --form "file=@$QA_TEST_DIR/demo.pdf;type=application/pdf" \
  --form 'mode=real' \
  --form 'confirm_external_processing=false'
```

Resultado esperado: HTTP 400, `detail.code` igual a `external_processing_not_confirmed`, sem
fallback para demo e sem chamada externa.

## 9. Walkthrough funcional no navegador

Abra `http://127.0.0.1:5173`.

| Ação | Resultado esperado |
|---|---|
| Abrir a home | Título “Avalie documentos com limites e evidências explícitos”; sem erro ou tela vazia |
| Inspecionar os cartões | “Avaliação de dissertações e teses” e “Buscar evidências” estão disponíveis |
| Inspecionar capacidades futuras | Documentos, busca semântica/RAG e Experimentos permanecem identificados como planejados |
| Abrir “Avaliação” | A rota muda para `/evaluation` sem HTTP 404 |
| Conferir os modos | Demo selecionado; modo real explica a indisponibilidade quando não há chave |
| Selecionar `demo.pdf` | O nome do arquivo aparece, mas nenhuma avaliação começa automaticamente |
| Acionar “Executar avaliação” | O documento é persistido, um run é criado e o estado muda de fila/execução para concluído |
| Conferir a URL | Contém `?run=<id>` sem expor caminho de arquivo ou credencial |
| Conferir o resultado | Faixa “Simulado — sem inferência LLM” e seis dimensões visíveis |
| Conferir a qualidade da extração | PDF digital informa texto extraído em todas as páginas; uma fixture mista sinaliza páginas candidatas a OCR/sem texto sem afirmar que estão vazias |
| Abrir “Busca” | A rota muda para `/search`, lista documentos persistidos e identifica o modo lexical sem LLM/embedding |
| Pesquisar uma expressão do PDF | O resultado mostra trecho, página, ID da unidade e score identificado apenas como ordenação lexical |
| Pesquisar uma expressão ausente | A tela apresenta zero resultados sem converter ausência em erro |
| Recarregar a página | O mesmo run e parecer são reabertos do backend, sem novo upload ou nova inferência |
| Conferir “Execuções recentes” | O run aparece com arquivo, modo simulado, provedor/modelo e estado |
| Acionar “Exportar JSON” | Um JSON é baixado com documento, run, `report.simulated: true` e Markdown identificado |
| Acionar “Exportar Markdown” | Um `.md` é baixado com identificação do modo, configuração, horários, consumo e parecer |
| Acionar “Imprimir” | A prévia de impressão contém somente o parecer e seus metadados, sem formulário, histórico ou comparação |
| Criar outra avaliação do mesmo `demo.pdf` | Um segundo run concluído aparece no histórico sem sobrescrever o primeiro |
| Selecionar os dois runs em “Comparação descritiva” | Configuração, horários, duração, consumo e seis dimensões aparecem lado a lado, sem declarar vencedor |
| Conferir o console | Nenhum erro da aplicação; warnings informativos devem ser registrados separadamente |

Falha, tela vazia, resultado parcial apresentado como sucesso ou capacidade planejada funcionando
como link reprovam esta etapa.

## 10. Responsividade e acessibilidade por teclado

| Ação | Resultado esperado |
|---|---|
| Usar viewport de 390 × 844 px | Painéis empilhados, texto legível e nenhuma rolagem horizontal causada pelo layout |
| Percorrer a tela com `Tab` e `Shift+Tab` | Ordem coerente entre navegação, modos, arquivo, execução e exportação |
| Observar cada elemento focado | Indicador de foco visível e labels que não dependem apenas de cor |
| Abrir o seletor e executar com teclado | Fluxo completo possível sem mouse |
| Executar uma busca com teclado | Consulta e resultado acessíveis sem mouse, preservando página e origem da evidência |
| Alcançar “Exportar JSON” após concluir | Controle focável e acionável pelo teclado |

Se qualquer passo falhar, registre a pendência em AC-008. O walkthrough visual sozinho não aprova
a acessibilidade por teclado.

## 11. Teste vetorial local opt-in

Este teste usa somente PDF sintético e inferência local, mas baixa aproximadamente centenas de MiB
no primeiro uso. Execute apenas com rede e espaço disponíveis:

```bash
QA_VECTOR_TEST_CONFIRM=download-local-model ./scripts/test-vector-search-live.sh
```

Resultado esperado:

- projeto Compose isolado inicia com pgvector e capacidade vetorial habilitada;
- consulta lexical de controle e consulta semântica recuperam a página anotada em top-1;
- a resposta identifica modelo, dimensão e versão de chunk;
- a segunda consulta reutiliza cache/índice;
- um resumo JSON registra latências observadas e `recall_at_1: 1.0` apenas para a fixture;
- nenhum provedor externo, chave, PDF real ou fallback lexical silencioso é usado;
- os contêineres e volumes isolados são removidos ao final.

O resultado é smoke funcional, não alegação de qualidade sobre dissertações reais. Registre a
medição no [baseline vetorial](../quality/vector-search-baseline.md).

## 12. Teste real opt-in

Esta seção é opcional e não deve ser executada para validar o perfil offline. Só prossiga se você
tiver confirmado:

- documento sintético, público ou autorizado;
- modelo permitido pela allowlist;
- quota disponível e política de faturamento da conta;
- consentimento consciente para enviar o texto extraído ao Google Gemini.

Configure a chave apenas no ambiente do processo que inicia o Compose, recrie a API e consulte
`/capabilities`. Não registre a chave neste documento ou em capturas. Na interface, selecione o modo
real, confirme o envio externo e execute o documento autorizado. Se `GEMINI_FALLBACK_API_KEY` estiver
configurada, o consentimento inclui um possível segundo envio após quota da principal.

O smoke sintético automatizado executa essas verificações em um projeto Compose isolado e remove
seus contêineres, volume e arquivos temporários ao final:

```bash
./scripts/test-gemini-live.sh
```

O script mostra quatro etapas. A chamada externa pode permanecer na etapa 4 por até 180 segundos;
ao falhar, informa a etapa e, quando disponível, o diagnóstico sanitizado da API. Um status `404`
no diagnóstico indica modelo indisponível para a chave/API e exige conferir `QA_GEMINI_MODEL` e a
allowlist; não é tratado como esgotamento de quota e não aciona a credencial reserva.

Resultado esperado:

- o modo real aparece disponível antes da execução;
- o resultado registra `mode: real`, `simulated: false`, provedor, modelo e uso real ou desconhecido;
- `usage.credential_slot` registra `primary` ou `fallback`, sem identificar conta ou chave;
- quota esgotada, timeout ou erro do provedor encerram a execução com erro explícito;
- nenhuma falha real é substituída silenciosamente por resultado demo.

Ao terminar, remova a chave do ambiente e recrie a API no perfil demo. Se qualquer condição de
segurança não estiver confirmada, marque esta etapa como “não executada — opt-in”.

## 13. Encerrar e conferir o repositório

Execute:

```bash
docker compose down --remove-orphans
docker compose --profile test run --rm \
  --volume "$PWD:/workspace:ro" \
  backend-tests \
  ruff check --no-cache --config /workspace/ruff.toml /workspace
git diff --check
git status --short
```

Resultado esperado:

- contêineres e rede do projeto são removidos;
- Ruff retorna `All checks passed!`; `notebooks/` e tooling fora do produto são excluídos pelo
  `ruff.toml` e não devem ser alterados;
- `git diff --check` termina sem erros;
- `git status` não contém arquivos gerados pelo teste dentro do repositório.

O diretório indicado por `$QA_TEST_DIR` contém somente fixtures e respostas descartáveis deste
roteiro. Remova-o depois de guardar as evidências necessárias.

## Diagnóstico de falhas

Se uma etapa falhar, registre primeiro:

```bash
docker compose ps
docker compose logs --no-color api web
```

Use a tabela para classificar o problema:

| Sintoma | Verificação | Resultado necessário para repetir |
|---|---|---|
| Docker daemon indisponível | `docker info` | Comando responde sem erro de conexão/permissão |
| Porta 8000 ou 5173 ocupada | Verificar processos/contêineres locais | Porta liberada ou conflito identificado conscientemente |
| Serviço `unhealthy` | Logs e healthcheck do serviço | Causa corrigida; não apenas aumento arbitrário de retries |
| Build falha ao baixar dependência | Conectividade e registry | Imagens/dependências disponíveis; testes continuam offline após o build |
| API falha, web funciona | Logs de `api` e chamada direta a `/health` | API saudável antes de testar o proxy |
| Proxy `/api` falha | Comparar health direto e pelo frontend | Ambos respondem HTTP 200 com o mesmo serviço |
| Teste automatizado falha | Primeira asserção/comando que falhou | Causa corrigida e `./scripts/test-containers.sh` inteiro aprovado |

Não apague volumes, imagens, arquivos ou mudanças do repositório como tentativa genérica de correção.

## Registro da execução

Preencha uma linha para cada etapa. Use “não executado” em vez de presumir aprovação.

| Etapa | Resultado esperado | Resultado observado | Evidência/observação | Estado |
|---|---|---|---|---|
| 2. Pré-requisitos | Docker/Compose/Git respondem | | | pendente |
| 3. Automação | Todas as suítes, builds e smoke passam | | | pendente |
| 4. Inicialização | API e web `healthy` em loopback | | | pendente |
| 5. HTTP/proxy/SPA | Health, capabilities e rotas respondem | | | pendente |
| 6. Fixture | PDF sintético criado fora do repositório | | | pendente |
| 7. Demo API | Resposta válida, simulada e determinística | | | pendente |
| 8. Falhas | Códigos HTTP e `detail.code` esperados | | | pendente |
| 9. Navegador | Fluxo persistente, reload, histórico e exportação funcionam | | | pendente |
| 10. Teclado/mobile | Fluxo acessível e layout responsivo | | | pendente |
| 11. Real opt-in | Resultado real ou erro explícito | `gemini-3.5-flash-lite`, uso real, 6 dimensões | Execução informada pelo mantenedor; 272 tokens de entrada e 880 de saída; slot `primary` | aprovado em 2026-09-13 |
| 12. Encerramento | Stack removida e repositório limpo de gerados | | | pendente |

Decisão final: `aprovado`, `aprovado com ressalvas` ou `reprovado`.

Para aprovação offline, as etapas 2 a 10 e 12 devem passar. A etapa 11 não é obrigatória.
