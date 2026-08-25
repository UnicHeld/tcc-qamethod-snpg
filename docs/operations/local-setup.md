# Configuração local

## Pré-requisitos

- Python 3.12
- Node.js 18+
- Qdrant (local ou cloud)
- Contas: Google AI (Gemini) e OpenAI (embeddings)

## Variáveis de ambiente

Copie o template e preencha os valores:

```bash
cp .env.example .env
```

Variáveis obrigatórias:

| Variável | Descrição |
|---|---|
| `GOOGLE_API_KEY` | Chave de API do Google AI (Gemini) |
| `OPENAI_API_KEY` | Chave de API da OpenAI (embeddings) |
| `DATABASE_URL` | URL do Qdrant (padrão: `http://localhost:6333`) |
| `QDRANT_API_KEY` | Chave de API do Qdrant (se cloud) |

Nunca versionar o `.env`. O `.gitignore` já o exclui.

## Ambiente virtual (raiz)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Usado para notebooks e ferramentas de análise.

## Serviço FastAPI

```bash
cd qa-services
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Healthcheck: `GET http://localhost:8000/`

## Interface React

```bash
cd qa-application
npm install
npm start
```

Acesso: `http://localhost:3000`

O CORS está configurado para aceitar apenas `http://localhost:3000`.

## Qdrant local

```bash
docker run -p 6333:6333 qdrant/qdrant
```

## Validação rápida

```bash
# Lint
ruff check .

# Testes
pytest
```
