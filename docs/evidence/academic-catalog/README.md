# Evidências do acervo acadêmico

Execução em 2026-11-21, somente com PDFs e dados sintéticos autorizados no banco temporário.
As imagens são capturas reais da aplicação local, sem mocks HTTP no walkthrough.

| Evidência | Verificação | Captura |
|---|---|---|
| Cadastro | Upload independente de avaliação e persistência de metadados manuais | [Cadastro](01-cadastro.png) |
| Busca entre trabalhos | Consulta por conhecimento recupera dois trabalhos do programa selecionado | [Dois trabalhos](02-busca-entre-trabalhos.png) |
| Filtro acadêmico | Ano inicial 2024 restringe o conjunto a um trabalho | [Filtro](03-filtro-ano.png) |
| Fonte verificável | Abertura da unidade original com documento, SHA256 e página | [Evidência](04-evidencia-original.png) |
| Mobile | Viewport 390 × 844, navegação legível e documento sem overflow horizontal | [Mobile](05-mobile.png) |

Playwright com Chromium 159 portátil: viewport desktop 1440 × 1000; mobile 390 × 844.
Nenhum evento `pageerror` durante o fluxo. Playwright MCP indisponível por ausência de Chrome;
instalação de sistema bloqueada, portanto browser e bibliotecas foram extraídos somente em `/tmp`.

Validação automatizada repetida para a PR:

- Ruff: aprovado.
- `pytest -p no:cacheprovider -m 'not live'`: **139 aprovados**, dois avisos de depreciação de dependências.
- `npm run typecheck`, `npm run lint`, `npm run test:run`, `npm run build`: aprovados; **25 testes**.
- `scripts/compose_smoke.py`: aprovado contra API, worker, Vite e PostgreSQL temporário no host;
  inclui catálogo, filtros, paginação, abertura e rejeição de fonte cruzada, além dos fluxos antigos.
- `git diff --check`: aprovado antes do commit.

O ambiente usou Python 3.12.14, Node 24.22.1, PostgreSQL 18.6 e pgvector 0.8.1.
Docker/Compose e backup/restore containerizado não foram executados por indisponibilidade da
integração Docker Desktop/WSL. O Compose fixa PostgreSQL 17/pgvector 0.8.6 e Node 24.20.0;
a validação local não substitui essa combinação de CI. Nenhum provedor externo foi chamado.

Requisitos e comandos detalhados na [especificação](../../specs/academic-catalog.md).
