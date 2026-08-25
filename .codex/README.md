# Workflows assistidos do TCC no Codex

Esta configuracao replica no Codex os workflows mantidos em `.claude/`, usando as superficies
nativas do produto:

- `AGENTS.md`: regras gerais e contratos do repositorio;
- `.codex/config.toml`: perfil de permissao do workspace, com escrita
  explicita em `.git` para permitir `git add`/`git commit` no sandbox;
- `.codex/hooks.json`: contexto carregado no inicio da sessao;
- `.codex/project.json`: comandos de validacao por tipo de arquivo.

Skills disponiveis:

- `$review-tcc`: revisa o diff com foco no metodo QA e pipeline RAG;
- `$pr`: prepara commits e pull request, com confirmacao antes de publicar;
- `$spec-driven`: cria especificacoes com requisitos e criterios de aceite rastreaveis;
- `$system-design`: projeta arquitetura, contratos, fluxos e trade-offs antes da especificacao.

As skills compartilhadas entre agentes ficam em `.agents/skills/` e seguem o processo canonico em
`docs/processes/spec-driven-development.md`.

A configuracao nao replica permissoes pessoais de `.claude/settings.local.json`,
nem credenciais ou conexoes locais.
