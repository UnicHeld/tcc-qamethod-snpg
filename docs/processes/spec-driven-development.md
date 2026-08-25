# Spec-driven e system design

## Objetivo

Transformar mudanças relevantes em contratos verificáveis antes de alterar o código, mantendo
rastreabilidade entre contexto, decisões, requisitos, implementação e validação.

O processo é proporcional ao risco. Correções locais, manutenção mecânica e documentação sem
mudança de comportamento não exigem uma nova especificação.

## Fluxo

```text
Solicitação
  -> triagem de impacto
  -> system design, se houver gate arquitetural
  -> especificação
  -> implementação
  -> validação e reconciliação documental
```

### 1. Triagem de impacto

Crie ou atualize uma especificação quando a mudança afetar comportamento observável, contrato de
API, modelo de dados, regra do método QA, pipeline RAG ou mais de um componente.

Passe primeiro por system design quando existir ao menos um destes fatores:

- novo componente, integração externa ou fronteira de responsabilidade;
- contrato público ou fluxo de dados novo ou incompatível;
- persistência, migração ou estratégia de consistência;
- trade-off material de segurança, privacidade, confiabilidade, desempenho ou custo;
- duas ou mais alternativas arquiteturais plausíveis com consequências duradouras.

### 2. System design

Registre a visão técnica em `docs/architecture/<slug>.md`, usando
`docs/architecture/system-design-template.md`. O documento deve referenciar apenas fatos
confirmados no repositório e separar claramente hipóteses e questões abertas.

Quando uma alternativa for escolhida, crie ou atualize a decisão correspondente em
`docs/decisions/<slug>.md`. A arquitetura descreve como o sistema funciona; a decisão explica por
que uma alternativa foi escolhida e quais consequências foram aceitas.

### 3. Especificação

Crie `docs/specs/<slug>.md` a partir de `docs/specs/spec-template.md`. Cada requisito recebe um ID
estável (`REQ-001`) e cada critério de aceite referencia o requisito que verifica. Requisitos devem
descrever comportamento e restrições, não antecipar detalhes internos sem necessidade.

Uma especificação está pronta para implementação quando:

- escopo incluído e excluído estão explícitos;
- requisitos e critérios de aceite são verificáveis;
- contratos, dados, segurança e falhas relevantes estão definidos;
- dependências e migrações estão identificadas;
- não há questão aberta que possa mudar a solução ou o comportamento esperado.

### 4. Implementação

O plano de implementação mapeia cada etapa aos requisitos afetados. O código deve permanecer no
menor escopo que satisfaz a especificação. Se a implementação revelar uma premissa incorreta ou
exigir mudança de contrato, atualize a especificação e, quando aplicável, o system design antes de
prosseguir.

### 5. Validação e reconciliação

Registre na especificação a evidência para cada critério de aceite: teste automatizado, comando,
inspeção ou experimento reproduzível. Não marque como validado o que não foi executado.

Ao finalizar:

- atualize o status da especificação;
- reconcilie documentação canônica afetada;
- reporte requisitos não validados, riscos residuais e desvios aprovados;
- não copie fatos canônicos para múltiplos documentos; use links.

## Estados

| Estado | Significado |
|---|---|
| `rascunho` | Escopo ou decisões ainda podem mudar. |
| `pronto` | Não há decisão bloqueante; pode ser implementado. |
| `em-implementacao` | Alterações de código estão em andamento. |
| `validado` | Critérios de aceite possuem evidência registrada. |
| `substituido` | Outro documento passou a ser a fonte vigente. |

O pedido explícito do usuário para implementar autoriza avançar de `rascunho` para execução no
mesmo fluxo somente quando não restar decisão bloqueante. Silêncio do usuário não resolve escolha
de produto, arquitetura ou risco material.
