# Recuperação vetorial local

- Status: aceita para o EV-02.
- Data: 2026-09-15.
- Relacionada a: [pipeline RAG](../architecture/rag-pipeline.md) e
  [recuperação do protótipo](../specs/prototype-recovery.md).

## Contexto

O EV-02 precisa recuperar conteúdo semanticamente relacionado em português sem API paga, preservar
a proveniência das unidades e não tornar a busca lexical dependente de modelo ou extensão vetorial.
O modelo candidato anterior, `intfloat/multilingual-e5-small`, tem 384 dimensões e limite de 512
tokens, mas o runtime do produto ainda não possuía inferência, cache ou versionamento de embeddings.

## Decisão

Usar PostgreSQL 17 com pgvector para os vetores derivados e FastEmbed/ONNX Runtime para inferência
local em CPU. O perfil inicial é:

- modelo `intfloat/multilingual-e5-small`, dimensão 384;
- artefato ONNX `model_O4.onnx`, evitando o runtime PyTorch e o peso ONNX integral;
- prefixos `query:` e `passage:` próprios da família E5;
- chunks `document-unit-v1` de até 384 tokens do tokenizer, com sobreposição de 64 tokens;
- distância cosseno e índice HNSW reconstruível;
- cache local do modelo em volume separado dos dados PostgreSQL.

O modo vetorial é opt-in por configuração. A primeira consulta de uma revisão cria seu índice de
forma síncrona e atômica; consultas seguintes reutilizam o perfil persistido. Alterar modelo,
dimensão ou chunk version cria outro perfil e nunca sobrescreve o anterior silenciosamente. A
busca lexical não instancia o embedder e continua disponível se o modelo, cache ou pgvector falhar.

## Consequências

O primeiro uso requer download aproximado de centenas de megabytes e pode ter latência relevante
em CPU. O endpoint deve expor modelo, dimensão e versão do chunk e deve retornar falha explícita,
sem fallback silencioso para lexical. O score cosseno é somente critério de ordenação, não
probabilidade ou confiança.

FastEmbed e os pesos do modelo passam a integrar o inventário de licenças da versão. O modelo e a
biblioteca possuem licença permissiva, mas a conferência final do artefato distribuído permanece
parte do EV-06.

## Alternativas descartadas nesta etapa

- `sentence-transformers`/PyTorch: runtime e imagem maiores para o mesmo primeiro experimento.
- embedding externo: exige transferência do texto e pode gerar custo, contrariando o laboratório
  local como baseline.
- Qdrant: adicionaria outro banco sem necessidade para o volume e os filtros atuais.
- embedding determinístico simulado: útil em testes, mas não demonstra recuperação semântica.

## Rollback

Desabilitar `QA_VECTOR_SEARCH_ENABLED` remove o modo da operação sem apagar dados. A tabela de
embeddings é derivada e pode ser reconstruída; a tabela de unidades e o índice lexical permanecem
como fontes independentes.
