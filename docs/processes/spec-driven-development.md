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

## Entregáveis de valor

O roadmap e os próximos passos são organizados por entregáveis de valor, não por componente,
biblioteca ou migração. Um entregável precisa declarar:

1. **Usuário e problema:** quem recebe valor e qual dificuldade concreta é reduzida.
2. **Resultado observável:** o que a pessoa consegue concluir de ponta a ponta ao final.
3. **Demonstração:** um fluxo curto, repetível e compreensível sem conhecer a implementação.
4. **Critérios de aceite:** evidências funcionais, de qualidade e operação que definem “pronto”.
5. **Limites:** capacidades próximas que continuam explicitamente fora da entrega.

Tarefas como adicionar pgvector, criar uma migração, instalar OCR, escrever um endpoint ou trocar
um parser são habilitadores técnicos. Elas pertencem a um entregável, mas não são valor entregue
isoladamente. Cada entregável deve atravessar somente os componentes necessários e terminar em um
estado utilizável; trabalho preparatório sem experiência disponível permanece marcado como tal.

O próximo entregável é escolhido pelo valor demonstrável e pela redução de risco. A numeração das
fases técnicas existentes continua válida para rastrear requisitos e dependências, mas não define
sozinha a prioridade do roadmap.

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

Para um entregável de valor, a especificação também identifica sua demonstração ponta a ponta e
separa critérios de conclusão dos habilitadores técnicos internos.

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
