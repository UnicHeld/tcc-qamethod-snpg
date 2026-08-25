# Instrucoes do projeto para o GitHub Copilot

Leia e siga `AGENTS.md` antes de analisar ou alterar o repositorio. Esse arquivo e a fonte canonica
para arquitetura, seguranca, escopo, Git, validacao e entrega.

## Spec-driven e system design

- Use `docs/processes/spec-driven-development.md` para funcionalidades ou mudancas que alterem
  comportamento observavel, contratos, dados ou mais de um componente.
- Antes da especificacao, produza system design quando houver decisao arquitetural, novo contrato,
  persistencia, integracao externa ou trade-off relevante de seguranca, confiabilidade, desempenho
  ou custo.
- Registre requisitos e criterios de aceite rastreaveis em `docs/specs/`, usando
  `docs/specs/spec-template.md`.
- Registre arquitetura em `docs/architecture/`, usando
  `docs/architecture/system-design-template.md`; decisoes e alternativas descartadas pertencem a
  `docs/decisions/`.
- Nao implemente uma especificacao enquanto houver decisao bloqueante em aberto.
- Correcoes locais e mudancas exclusivamente documentais podem dispensar novos artefatos; declare
  essa decisao no plano ou na entrega.

Preserve alteracoes locais nao relacionadas, nao acesse `.env*` e nao execute commit, push ou
operacoes destrutivas sem solicitacao explicita.
