# Pipeline de avaliação

## Fluxo ponta a ponta

```
POST /evaluation/upload (PDF)
  └─ ParserService.extrair_texto()        → texto bruto
  └─ EvaluationService.evaluation_generate()
       └─ prompt com dimensões + texto
       └─ Gemini 1.5 Flash (stream=True)
  └─ StreamingResponse → cliente
```

## Contrato de entrada

`POST /evaluation/upload`

- `Content-Type: multipart/form-data`
- Campo `file`: PDF (`application/pdf`)
- Retorno: `text/plain` em streaming com a análise estruturada

Erros:
- `400` — arquivo não é PDF
- `500` — falha na extração ou na geração

## Serviços envolvidos

| Serviço | Arquivo | Responsabilidade |
|---|---|---|
| `ParserService` | `services/parser_service.py` | extração de texto de PDFs |
| `EvaluationService` | `services/evaluation_service.py` | montagem do prompt e chamada ao Gemini |
| `QdrantManager` | `services/qdrant_manager.py` | indexação e recuperação vetorial (RAG) |
| `Embedder` | `services/embedder.py` | geração de embeddings via OpenAI |

## Streaming

A resposta é entregue em chunks via `StreamingResponse`. O cliente React consome o stream
e exibe o texto progressivamente. Não há buffer acumulado no servidor.

## Prompt do avaliador

O prompt é definido em `EvaluationService.evaluation_generate()`. Ele instrui o modelo a:

- apresentar o título do documento;
- analisar cada dimensão com nota ao final;
- omitir informações pessoais (autor, orientador);
- ser objetivo e imparcial.

Alterações no prompt devem ser acompanhadas de validação com o conjunto de documentos de referência
em `notebooks/rag-validation/`.
