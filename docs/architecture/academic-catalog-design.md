# Acervo acadêmico consultável

- **Status:** `implementado; validado na automação local`
- **Última atualização:** 2026-11-21
- **Especificação:** [Acervo acadêmico](../specs/academic-catalog.md)
- **Decisão:** [Continuidade do Question Answering](../decisions/restore-question-answering-focus.md)

## Contexto e objetivos

Os PDFs admitidos já têm revisão SHA256 imutável, unidades de texto por página e índice GIN
em português. Falta identificar os trabalhos academicamente e consultar diferentes documentos.
A primeira entrega permite catalogar uma coleção autorizada e abrir evidências recuperadas,
independentemente de avaliação individual ou chamada de LLM.

Não inclui síntese, embeddings entre documentos, OCR, download do PDF original, coleta externa,
autenticação ou isolamento entre universidades. O perfil vigente continua local e compartilhado.

## Fluxo e responsabilidades

1. React admite um PDF digital pelo contrato existente de documentos; não cria um parecer.
2. O usuário cadastra metadados de origem manual e uma URL de origem opcional.
3. FastAPI valida os campos e grava uma entrada vinculada à revisão documental no PostgreSQL.
4. A listagem e a busca aplicam os mesmos filtros acadêmicos. Somente documentos catalogados
   participam dessa coleção: um upload isolado não publica automaticamente um trabalho no acervo.
5. A busca lexical consulta unidades de todos os documentos elegíveis usando o índice existente.
6. Cada resultado identifica trabalho, revisão do conteúdo, revisão dos metadados, unidade e página.
   A abertura da evidência lê exclusivamente a unidade daquele documento.

## Interfaces e dados

Prefixo `/api/v1/catalog`:

- `PUT /documents/{document_id}` recebe `{metadata, expected_revision}`. Criação usa revisão 0;
  alteração exige a revisão atual. Divergência retorna 409 e exige reabertura antes de salvar.
- `GET /documents` recebe filtros, `limit` (1–100, padrão 20) e `offset` (>=0). Retorna
  `{entries, total, limit, offset}`; `total` conta todos os trabalhos que satisfazem os filtros.
- `GET /documents/{document_id}` retorna uma entrada ou 404.
- `POST /search` recebe `{query, filters, limit, offset}`. Consulta de 1–200 caracteres úteis,
  limite 1–50 (padrão 10). Retorna `{query, filters, retrieval_mode:"lexical", hits,
  total_hits, total_documents, limit, offset}`. Totais referem-se às correspondências, não à
  cobertura de uma universidade ou do SNPG.
- `GET /documents/{document_id}/evidence/{unit_id}` retorna `{entry, unit_id, page, text}`.
  Documento não catalogado ou unidade de outro documento resulta em 404.

O offset de listagem e busca é limitado a 1.000.000. Paginação por cursor é evolução futura.

Uma entrada tem `{document, metadata, metadata_revision, metadata_source:"manual", updated_at}`;
`document` mantém o schema existente. `metadata` contém título obrigatório (até 500 caracteres),
tipo opcional (`thesis`, `dissertation`, `other`), ano opcional (1600–2100), área, instituição,
programa, autor, orientador e coorientador opcionais (até 300 caracteres cada) e `source_url`
opcional (URL HTTP/HTTPS, até 2000 caracteres). Vazio opcional vira nulo; campos extras são
rejeitados. Não se infere título confirmado pelo nome do arquivo.

Filtros: `document_type`, `year_from`, `year_to`, `area`, `institution`, `program`, `author`,
`advisor`, `coadvisor`. Intervalo de ano é inclusivo e não pode ser invertido. Texto usa igualdade
sem distinção entre maiúsculas e minúsculas, após remoção dos espaços nas extremidades; não há
sinônimos nem remoção de acentos. Campos desconhecidos não satisfazem filtros preenchidos.

Cada hit tem `{entry, unit_id, page, snippet, score}`. Ordenação: relevância decrescente,
document_id, página, unit_id. Trecho tem até 320 caracteres. Paginação não corta silenciosamente
o conjunto usado para filtrar ou calcular os totais.

Migração aditiva `0009_academic_catalog.sql` cria `academic_catalog` com FK para `documents`,
metadados, origem manual, revisão inteira e timestamp. A atualização integral é atômica e usa
controle otimista. Metadados não alteram texto, SHA ou índices por documento. URLs são referências;
o servidor não as acessa. APIs anteriores permanecem compatíveis; CORS passa a aceitar PUT.

## Segurança, confiabilidade e operação

SQL parametrizado; tamanho de consultas, campos e páginas limitado. Documento ausente retorna
404; conflito, 409; corpo inválido, 422; indisponibilidade do banco, 503 com erro estruturado.
O acervo não envia texto a provedores. URL de origem não autoriza coleta nem serve como evidência
de autorização de uso. O operador deve admitir somente documentos autorizados.

Entradas sem metadados permanecem fora do acervo. Metadados são declarações manuais revisáveis,
não extração validada. A revisão de metadados localiza o estado mostrado na busca; esta entrega
não congela um histórico de respostas. O detalhe mostra a revisão atual, permitindo detectar
alteração de metadados desde o resultado. A revisão documental mantém a evidência estável.

## Alternativas e rollout

Expandir os contratos por documento misturaria comportamento novo com serviços existentes.
Indexar todo o acervo vetorialmente em cada busca imporia processamento e downloads inesperados.
Um módulo de catálogo separado reutiliza PostgreSQL/FTS sem essas dependências; a decisão segue
a ADR vigente e não introduz um novo banco ou provedor.

Aplicar migração antes da API nova. Documentos existentes continuam válidos e podem ser
catalogados manualmente. Reversão da aplicação mantém a tabela adicional sem excluir dados.
Testes offline de contrato, integração PostgreSQL e interface devem cobrir filtros, conflitos,
paginação, escopo de evidências e regressão das APIs antigas.

Evidências e limitações da execução estão na [especificação](../specs/academic-catalog.md#plano-de-validação).

## Questões abertas

Nenhuma bloqueante para esta entrega. Isolamento SaaS e conectores são entregas posteriores.
