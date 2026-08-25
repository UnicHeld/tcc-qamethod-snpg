# Configuração do Cursor

`AGENTS.md` é a fonte canônica das instruções do projeto. As regras em `rules/` apenas garantem
que o Cursor carregue esse contexto e aplique convenções específicas por tipo de arquivo.

## Regras

- `rules/project.mdc`: regra global, aplicada em todas as conversas do projeto.
- `rules/python.mdc`: convenções adicionais para arquivos Python.
- `rules/spec-driven.mdc`: requisitos e critérios de aceite para mudanças de comportamento.
- `rules/system-design.mdc`: desenho arquitetural e decisões técnicas relevantes.

As regras especializadas usam o processo e os templates canônicos em `docs/`.

Configurações pessoais, credenciais e conexões MCP não devem ser versionadas neste diretório.
