# Pipeline de avaliação

- Estado: avaliação direta F1/F2/F3 e qualidade de página F4a implementadas; insight RAG é um fluxo
  separado e não altera este avaliador.
- Contrato provisório: [roteiro de recuperação](../specs/prototype-recovery.md#contrato-de-retomada-f1).

## Fluxo ponta a ponta

```text
POST /evaluation/upload (PDF + modo + confirmação)
  ├─ valida MIME, bytes e limite de upload
  ├─ ParserService.extract_text() → revisão, unidades, qualidade por página e SHA-256
  ├─ adaptador selecionado
  │    ├─ demo → resultado determinístico identificado
  │    └─ real → Gemini sob demanda, após chave/allowlist/consentimento
  ├─ validação do parecer → seis dimensões, notas/insuficiência e evidências
  └─ EvaluationResponse → relatório tipado + Markdown derivado + uso
```

O caminho ativo avalia o documento direto. `QdrantManager` e `Embedder` são código experimental
legado, não são importados pelo entrypoint e não participam desse fluxo.

O EV-03 gera respostas de pergunta única a partir de um pacote recuperado, sob contrato próprio em
[insights RAG](rag-insights-design.md). Ele não produz `EvaluationReport` nem notas nas dimensões.

O fluxo persistente consumido pela interface é:

```text
POST /api/v1/documents → POST /api/v1/runs → queued
  └─ worker local → running → succeeded | failed
       └─ GET /api/v1/runs/{id}/result após succeeded
```

Na admissão persistente, cada página recebe `extracted`, `ocr_candidate` ou `no_text`, além da
contagem de caracteres e do sinal de imagem raster. A classificação pode ser reaberta em
`GET /api/v1/documents/{id}/pages`. `ocr_candidate` não comprova ilegibilidade e não executa OCR;
`no_text` também não afirma que a página esteja semanticamente vazia.

No início, o worker converte runs abandonados em `running` para `interrupted`; ele não repete uma
chamada externa automaticamente.

## Contrato de entrada e saída

`POST /evaluation/upload` recebe `multipart/form-data`:

| Campo | Tipo | Regra |
|---|---|---|
| `file` | PDF | Até 20 MiB e 300 páginas por padrão; precisa ter texto extraível |
| `mode` | `demo` ou `real` | `demo` é o padrão |
| `confirm_external_processing` | booleano | Obrigatório como `true` no modo real |

A resposta registra modo, marcação de simulação, provedor/modelo, versão do prompt, metadados do
documento, referências públicas das unidades, relatório estruturado, Markdown derivado e consumo
`simulated`, `actual` ou `unknown`. Cada referência pública contém somente ID e página; o PDF e o
texto extraído não são devolvidos nem persistidos.

Esse contrato provisório continua sem persistência. Separadamente, `POST /api/v1/documents` admite
e persiste metadados/unidades no PostgreSQL; `POST /api/v1/runs` vincula uma avaliação ao documento
e `GET /api/v1/runs/{id}` e `GET /api/v1/runs/{id}/result` permitem acompanhar e reabrir o
resultado. A rota `/evaluation/upload` permanece somente como compatibilidade temporária.

`GET /health` verifica somente liveness. `GET /capabilities` informa limites, modo padrão e motivo
de indisponibilidade da inferência real sem expor a credencial.

## Falhas

Erros usam `detail.code` e `detail.message` e não são convertidos em resultado parcial:

- `400`: arquivo vazio ou ausência de confirmação externa;
- `413`: limite de bytes ou páginas excedido;
- `415`: tipo de mídia não suportado;
- `422`: PDF inválido ou sem texto extraível;
- `429`: quota do provedor indisponível;
- `502`: falha ou resposta vazia do provedor;
- `503`: chave ausente ou modelo fora da allowlist;
- `504`: timeout de parsing ou de inferência.

## Prompt e adaptadores

O prompt e sua versão ficam em `services/evaluation_service.py`. A instrução técnica separa o
conteúdo não confiável do documento e preserva as seis dimensões, a nota de 0 a 10, a omissão de
informações pessoais e a proibição de nota final agregada.

O adaptador demo ignora instruções do documento e produz um `EvaluationDraft` fixo e marcado. O
adaptador real usa `google-genai`, modelo configurável, cliente criado somente após a seleção do
modo e resposta JSON solicitada pelo schema. Ambos passam pela mesma validação de domínio antes da
renderização. Resposta vazia, JSON inválido, evidência externa à revisão ou ausência de chave
encerram a execução. Um erro de quota pode usar uma única credencial reserva configurada de outro
projeto gratuito; não há fallback para outro erro, modelo, plano pago ou simulação. A resposta
registra apenas o slot `primary` ou `fallback`.

Alterações da rubrica exigem validação acadêmica conforme
[método de avaliação](../quality/evaluation-method.md). A qualidade semântica das evidências ainda
depende de corpus autorizado e revisão humana.
