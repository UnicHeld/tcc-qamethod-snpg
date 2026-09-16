# QA Application

Interface React/Vite do laboratório local QA Method. A rota `/evaluation` permite selecionar um
PDF digital, escolher o modo demo ou real autorizado, executar a avaliação e exportar o resultado
estruturado em JSON. A tela persiste documentos e runs, acompanha o worker, mantém o run na URL e
lista execuções recentes para reabertura após reload. A rota `/search` compara recuperação lexical
e vetorial. A rota `/insights` cria uma pergunta persistente, acompanha o worker e apresenta uma
resposta baseada no pacote congelado, com página, origem e exportações JSON/Markdown.

## Execução

Pelo Compose na raiz do repositório (recomendado):

```bash
docker compose up --build
```

Para hot reload, combine `compose.yaml` e `compose.dev.yaml`, conforme a
[configuração local](../docs/operations/local-setup.md).

Alternativamente, no host:

```bash
mise install
npm ci
npm run dev
```

A interface abre em `http://127.0.0.1:5173` e espera a API em `http://127.0.0.1:8000`. Para outra
URL local, configure `VITE_API_BASE_URL`. Nunca use variáveis `VITE_` para segredos, porque elas são
incluídas no bundle do navegador.

## Qualidade

```bash
npm run typecheck
npm run lint
npm run test:run
npm run build
```

O modo demo não exige credenciais e deve aparecer sempre como “Simulado — sem inferência LLM”.
A busca lexical está disponível e a vetorial é opt-in. Insights RAG possuem fluxo próprio; judge
ainda é planejado. Runs
concluídos do mesmo documento podem ser comparados de forma descritiva e exportados em JSON ou Markdown.
Na avaliação persistente, a interface também mostra cobertura de texto por página e sinaliza
candidatas a OCR ou páginas sem texto detectado, sem executar OCR implicitamente.
