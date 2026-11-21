# Escolha histórica do LLM avaliador

- Status: `histórica`; configuração fixa e streaming substituídos pelo adaptador atual.
- Escopo: avaliador direto do protótipo, não o serviço principal de QA do TCC.
- Configuração atual: [pipeline de avaliação](../architecture/evaluation-pipeline.md) e
  [configuração local](../operations/local-setup.md).
- Direção do projeto: [continuidade do Question Answering](restore-question-answering-focus.md).

O conteúdo abaixo preserva o registro anterior. No estudo de 2024, Gemini era usado na extração
estruturada e GPT-4o mini na geração do serviço de QA, conforme o
[histórico do TCC](../history/tcc-2024.md). A escolha de Gemini no avaliador não descreve toda
a arquitetura acadêmica nem impõe o modelo vigente.

## Decisão

Usar **Gemini 1.5 Flash** como modelo avaliador principal.

## Critérios avaliados

| Critério | Peso |
|---|---|
| Custo por token | alto |
| Suporte a streaming | obrigatório |
| Janela de contexto | alto (documentos longos) |
| Qualidade em tarefas analíticas de texto acadêmico | alto |
| Latência | médio |

## Alternativas consideradas

| Modelo | Motivo de descarte |
|---|---|
| GPT-4o | custo mais alto para volume de experimentos do TCC |
| Claude 3 Haiku | sem acesso via API no período de desenvolvimento |
| Llama 3 (local) | latência e custo de infraestrutura local |

## Configuração histórica

- `model_name`: `gemini-1.5-flash`
- `temperature`: `0.1` — baixa para maximizar consistência entre execuções
- `stream`: `True` — necessário para UX progressiva no frontend

## Critério de revisão do registro original

Reavaliar se o custo ou disponibilidade do Gemini mudar, ou se experimentos mostrarem
variância acima do aceitável entre execuções com temperatura baixa.
