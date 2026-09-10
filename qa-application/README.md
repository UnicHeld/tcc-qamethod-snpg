# QA Application

Interface React/Vite do laboratório local QA Method. A rota `/evaluation` permite selecionar um
PDF digital, escolher o modo demo ou real autorizado, executar a avaliação e exportar o resultado
estruturado em JSON.

## Execução

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
Histórico persistente, busca/RAG e judge ainda são recursos planejados.
