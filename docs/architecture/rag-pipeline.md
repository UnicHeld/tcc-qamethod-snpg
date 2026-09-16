# Pipeline RAG

- Estado: buscas EV-01/EV-02 ativas e insight RAG EV-03 validado na automação integrada e no
  walkthrough visual; apenas a inferência real opt-in permanece pendente.
- Evolução em curso: F5 do [roteiro de recuperação](../specs/prototype-recovery.md).

## Intenção

RAG (Retrieval-Augmented Generation) usa unidades verificáveis para responder uma pergunta única
sem alterar a avaliação direta. O pacote recuperado é congelado antes da geração e cada citação é
validada contra ele.

```text
Ativo: unidades versionadas → lexical ou embedding local/pgvector → hits verificáveis
                                                                  ↓
       pergunta → run assíncrono → pacote congelado E1..En → demo/Gemini → resposta citável
```

## Código existente e limites

`services/qdrant_manager.py` e `services/embedder.py` preservam um experimento anterior com Qdrant
e embeddings OpenAI. Eles documentam a POC, mas não serão reativados no pipeline planejado. Esses
módulos:

- não são importados por `app.main`;
- não estão nas dependências isoladas do serviço recuperado;
- não possuem contrato de unidades/evidências usado pela API;
- usam operações e configuração que precisam ser revistas antes de qualquer ativação.

Os notebooks antigos permanecem apenas como arquivo histórico da POC. Não serão migrados ou
reexecutados e seus resultados não são evidência do pipeline atual. A validação futura de RAG será
recriada com fixtures e testes automatizados no componente responsável.

## Contrato atual

O EV-01 expõe `POST /api/v1/search`: recebe documento, consulta e limite, pesquisa apenas as
unidades daquela revisão com full-text search em português e devolve página, ID, trecho curto,
score e `retrieval_mode: "lexical"`. A ordenação é determinística e a chamada não usa LLM,
embedding nem persistência do texto consultado.

No EV-02, o perfil vetorial opcional reutiliza o PostgreSQL local com a extensão pgvector.
Embeddings derivados e versionados referenciam as unidades existentes; dimensão do vetor, modelo e
parâmetros de chunk são registrados. O contrato é ampliado de forma aditiva para identificar o modo
vetorial, preservando o modo lexical. A configuração escolhida está registrada na
[decisão de recuperação vetorial](../decisions/local-vector-retrieval.md).

A extensão e o índice vetorial entram por migração própria, sem recriar ou sobrescrever dados já
persistidos. Se pgvector estiver indisponível, a busca lexical e a avaliação direta/demo continuam
funcionando. O perfil não usa chave de embeddings; o download do modelo local ocorre somente no
primeiro uso consciente. Medições e limites estão no
[baseline vetorial](../quality/vector-search-baseline.md).

No EV-03, `POST /api/v1/insights` persiste documento, pergunta, modo lexical/vetorial, limite e
modo demo/real. O worker recupera os hits, cria IDs locais `E1..En`, preserva unidade, página,
trecho e score e envia somente esse pacote ao gerador. `GET /api/v1/insights/{id}/result` só
publica pacote, resposta e Markdown após validar revisão, pergunta e citações. O desenho e os
limites estão em [insights RAG rastreáveis](rag-insights-design.md).

A automação containerizada cobre domínio, adaptadores, PostgreSQL, API, worker, interface, smoke e
backup/restore. O walkthrough do EV-03 passou em desktop e 390 × 844 px, sem erros da aplicação ou
violações detectadas pelo axe-core.
