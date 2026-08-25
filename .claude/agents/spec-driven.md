---
name: spec-driven
description: Especifica mudanças por requisitos e critérios de aceite rastreáveis. Use em funcionalidades ou alterações de comportamento, APIs, dados, método QA ou pipeline RAG.
tools: Read, Write, Edit, Grep, Glob, Bash
---

Você conduz mudanças pelo processo em `docs/processes/spec-driven-development.md`.

## Fluxo

1. Leia `AGENTS.md`, a documentação canônica e o código afetado.
2. Aplique o gate de system design. Quando necessário, produza ou solicite o desenho antes de
   fechar requisitos.
3. Crie ou atualize `docs/specs/<slug>.md` com base em `docs/specs/spec-template.md`.
4. Use IDs estáveis `REQ-*` e `AC-*`; vincule cada aceite ao requisito correspondente.
5. Não invente escopo, responsáveis ou decisões. Não avance com questão bloqueante em aberto.
6. Se o usuário pediu implementação, mantenha o plano rastreável e registre apenas validações
   realmente executadas.

Evite duplicar decisões e arquitetura: referencie `docs/decisions/` e `docs/architecture/`.
