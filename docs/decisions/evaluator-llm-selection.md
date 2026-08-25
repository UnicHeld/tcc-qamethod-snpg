# Escolha do LLM avaliador

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

## Configuração vigente

- `model_name`: `gemini-1.5-flash`
- `temperature`: `0.1` — baixa para maximizar consistência entre execuções
- `stream`: `True` — necessário para UX progressiva no frontend

## Revisão

Reavaliar se o custo ou disponibilidade do Gemini mudar, ou se experimentos mostrarem
variância acima do aceitável entre execuções com temperatura baixa.
