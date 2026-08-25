# Pipeline RAG

## Visão geral

O pipeline RAG (Retrieval-Augmented Generation) indexa documentos de referência no Qdrant
e os recupera para enriquecer o contexto do avaliador.

```
Documentos de referência → Embedder (OpenAI) → Qdrant (coleção vetorial)
                                                        ↓
PDF novo → extração → consulta Qdrant → chunks relevantes → prompt enriquecido → Gemini
```

## Componentes

### QdrantManager (`services/qdrant_manager.py`)

- Gerencia conexão com Qdrant (URL e API key via variáveis de ambiente).
- Cria coleções com tamanho de vetor e métrica de distância configuráveis.
- Insere documentos a partir de arquivos JSON com campo `embedding`.
- Realiza buscas por similaridade e retorna chunks relevantes.
- Gera IDs determinísticos via SHA-256 do conteúdo para evitar duplicatas.

### Embedder (`services/embedder.py`)

- Gera embeddings via API OpenAI.
- Configurado com `OPENAI_API_KEY` via variável de ambiente.

## Configuração do Qdrant

| Parâmetro | Valor padrão | Fonte |
|---|---|---|
| URL | `http://localhost:6333` | `DATABASE_URL` no `.env` |
| API key | — | `QDRANT_API_KEY` no `.env` |
| Métrica de distância | Cosseno | parâmetro de `create_collection` |

## Notebooks de validação

Os experimentos de validação do RAG estão em `notebooks/rag-validation/`. Eles medem
precisão de recuperação e impacto no score de avaliação final.
