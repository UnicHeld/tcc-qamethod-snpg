# Baseline da recuperação do protótipo

- Data da inspeção: 2026-09-09.
- Escopo: F0 do [roteiro de recuperação](../specs/prototype-recovery.md).
- Estado do Git: havia alterações documentais locais da própria iniciativa; foram preservadas.

## Estado inicial observado

Atualização de acompanhamento em 2026-09-13: o mantenedor informou que executou o runbook
containerizado com sucesso, exceto a seção 11 (inferência real). Essa é evidência declarada pelo
mantenedor, incluindo navegador, exportação e teclado; a fotografia F0 abaixo permanece histórica.
Naquele momento o mantenedor ainda não possuía chave de LLM gratuito; isso não bloqueou a
implementação nem os testes offline da F2. Em 2026-09-13, posteriormente, o mantenedor configurou
duas credenciais Gemini de projetos distintos e concluiu o smoke real com a credencial principal.

Atualização de implementação em 2026-09-13: a F2 foi concluída offline. O parser agora preserva
unidades por página, demo e Gemini compartilham o parecer estruturado e a rota pública devolve
referências sem texto, `report` tipado e Markdown derivado. A suíte containerizada passou com 39
testes backend e 1 teste frontend. O adaptador Gemini foi exercitado com cliente falso; nenhuma
inferência externa havia sido executada nessa validação offline. Depois dela, o smoke opt-in com
fixture sintética passou em `gemini-3.5-flash-lite`, registrando uso real e seis dimensões; AC-003
deixou de estar pendente.

| Área | Evidência antes da implementação | Consequência |
|---|---|---|
| Runtime | Python global 3.14.7, Node 24.20.0, npm 11.19.0 e uv 0.12.10 | O serviço não deve usar o Python global |
| Backend | `requirements.txt` e `Dockerfile` vazios; nenhum teste da aplicação | Instalação e baseline não eram reproduzíveis |
| Avaliador | `google-generativeai`, modelo fixo, cliente no import e erros engolidos | Boot dependia implicitamente de credencial e stream podia terminar vazio |
| Parser | PyPDF2 + pikepdf, texto concatenado e erro genérico | PDF inválido e PDF sem texto não eram diferenciados |
| Frontend | CRA 5, URL fixa na porta 8000, upload iniciava avaliação | Build legado e ausência de configuração/consentimento explícitos |
| Capacidades | Links `#` para recursos ausentes | A interface apresentava funções planejadas como acionáveis |

Não foram executados notebooks nem instaladas as dependências antigas da raiz para produzir este
inventário. Nenhum documento real foi copiado para fixtures.

## Isolamento adotado para F1

- Backend: Python 3.12.14 e uv 0.12.10 declarados em `qa-services/mise.toml`; dependências diretas
  no `pyproject.toml`, lock do uv e grupos separados de runtime/desenvolvimento.
- Frontend: Node 24.20.0 declarado em `qa-application/mise.toml`; Vite e dependências diretas no
  lock do npm. O bundle recebe apenas `VITE_API_BASE_URL`, nunca credenciais.
- Fixtures: PDFs sintéticos são construídos em memória pelos testes; há casos digital, sem texto e
  inválido. O ignore global de PDFs permanece restritivo.
- Runtime futuro: `qa-services/runtime/` está ignorado; nenhuma persistência foi introduzida em F1.

## Dependências diretas da fatia

| Backend | Uso |
|---|---|
| FastAPI, Uvicorn, python-multipart | API HTTP local e upload multipart |
| pypdf | PDF digital e contagem de páginas |
| google-genai | Adaptador Gemini opt-in |
| python-dotenv | Configuração local somente no backend |
| pytest, httpx, Ruff | Testes offline e lint no grupo de desenvolvimento |

| Frontend | Uso |
|---|---|
| React, React DOM, React Router | SPA e duas rotas existentes |
| React Markdown, React Icons | Exibição segura do parecer e ícones |
| Vite, TypeScript, ESLint, Vitest, Testing Library | Build, tipos, lint e testes |
| Tailwind CSS, PostCSS, Autoprefixer | Estilos existentes preservados na migração |

Qdrant, OpenAI, OCR e bibliotecas de notebooks não fazem parte do caminho de boot da F1. Licenças
e avisos completos serão consolidados no inventário técnico da F7.
