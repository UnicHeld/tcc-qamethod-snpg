# Judge separado de pareceres

- **Status:** `implementado` nos modos demo offline e real opt-in; qualidade semântica pendente
- **Última atualização:** 2026-09-16
- **Especificação relacionada:** [judge separado](../specs/judge-runs.md)

## Contexto

Os pareceres persistidos já podem ser reabertos e comparados, mas a comparação apenas apresenta
dois resultados. O EV-05 exige uma auditoria separada, rastreável e incapaz de alterar o parecer
fonte. O fluxo real usa um segundo modelo, diferente do avaliador, para criticar o parecer contra a
rubrica e as evidências citadas. Qualidade semântica continua condicionada a corpus autorizado e
revisão humana.

## Decisão

O judge usa um recurso e uma fila próprios:

```text
POST /api/v1/judge-runs -> cópia atômica do parecer + evidências citadas + queued
  -> worker valida os snapshots e executa o adaptador demo ou Gemini
  -> valida achados contra dimensões/evidências do snapshot
  -> persiste JudgeReport + Markdown sem atualizar evaluation_runs
  -> GET /api/v1/judge-runs/{id}/result
```

`judge_runs` referencia um `evaluation_run` concluído, mas também congela seu `report` JSONB e o
texto das `document_units` citadas. O hash SHA-256 da representação JSON canônica identifica
exatamente o parecer auditado. O juiz nunca consulta o PDF ou unidades adicionais durante a
inferência. Reexecuções criam outro judge run; interrupções não repetem trabalho silenciosamente.

## Contrato

- `POST /api/v1/judge-runs`: `source_run_id`, `mode` e confirmação do processamento externo quando
  `mode: "real"`; aceita `Idempotency-Key`.
- `GET /api/v1/judge-runs`: histórico recente, com filtro opcional por parecer fonte.
- `GET /api/v1/judge-runs/{id}`: configuração e estado, sem resultado parcial.
- `GET /api/v1/judge-runs/{id}/result`: snapshot fonte, relatório validado e Markdown após sucesso.

Cada achado possui ID local sequencial, critério, severidade, dimensão opcional, explicação e IDs
de evidências do parecer fonte. O contrato valida referências, mas não afirma que a evidência
sustenta semanticamente a justificativa.

## Segurança e confiabilidade

O modo demo não envia dados para provedores. O modo real exige consentimento explícito e só fica
disponível com chave, allowlist e `QA_JUDGE_GEMINI_MODEL` diferente de `QA_GEMINI_MODEL`. O payload
externo contém o parecer congelado e apenas seus trechos citados. Ambos são delimitados como dados
não confiáveis; o prompt proíbe seguir instruções neles. Markdown é derivado de objetos validados e
não renderiza HTML arbitrário. Falha, interrupção ou resultado inválido nunca publica relatório
parcial. A reserva é usada uma única vez e somente após erro de quota; não há troca de modelo nem
fallback silencioso para demo.

O judge avalia três critérios explícitos: alinhamento entre afirmações e evidências, consistência
interna do parecer e conformidade com a rubrica das seis dimensões. A saída estruturada ainda passa
pelas mesmas validações de IDs, dimensões e referências antes da publicação atômica.

## Alternativas

| Alternativa | Resultado |
|---|---|
| Alterar o parecer original com correções | Descartada: perde rastreabilidade e viola o EV-05 |
| Reusar `evaluation_runs` | Descartada: mistura contratos, prompts e resultados diferentes |
| Judge síncrono no endpoint | Descartada: timeout e falhas externas pertencem ao worker |
| Fila e snapshot próprios | Escolhida: separação, idempotência e auditoria reproduzível |
| Mesmo modelo do avaliador e do judge | Descartada nesta fatia: reduz independência da crítica |
| Enviar o PDF completo ao judge | Descartada: amplia exposição e permite evidência fora do parecer |

## Evolução posterior

Executar o smoke real com fixture autorizada e construir uma amostra humana com erros controlados
para medir precisão dos achados. Só então comparar modelos, definir limiares e fazer alegações de
qualidade. O judge continua sendo apoio à revisão, não banca ou correção automática.
