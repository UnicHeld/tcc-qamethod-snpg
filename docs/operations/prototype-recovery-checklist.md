# Checklist da recuperação do protótipo

- Atualizado em: 2026-09-16.
- Escopo desta fotografia: F0, F1, F2, F3a–F3d, F4a–F4c, EV-01–EV-03 da F5 e o
  judge demo/real opt-in do EV-05/F6 do
  [roteiro de recuperação](../specs/prototype-recovery.md).
- Legenda: `[x]` concluído com evidência; `[ ]` ainda pendente. Itens parciais descrevem
  explicitamente o que falta.

Este checklist é a visão rápida do progresso. Requisitos, critérios de aceite e evidências
detalhadas permanecem canônicos na [especificação](../specs/prototype-recovery.md). Para repetir a
validação, siga o [roteiro de testes](prototype-recovery-test-plan.md).

## F0 — baseline e isolamento

- [x] Estado inicial e riscos registrados no
  [baseline](prototype-recovery-baseline.md).
- [x] Backend isolado em Python 3.12.14 com `mise`, `uv`, manifesto próprio e lock.
- [x] Frontend isolado em Node.js 24.20.0 com `mise`, npm e lock.
- [x] Dependências de runtime e desenvolvimento separadas no backend.
- [x] Fixtures sintéticas para PDF digital, PDF sem texto e PDF inválido.
- [x] Diretório futuro de runtime ignorado pelo Git sem liberar PDFs reais no repositório.
- [x] Configuração de segredos restrita ao backend e documentação operacional reconciliada.

## F1 — backend

- [x] Boot da API e `/health` sem credencial ou chamada ao provedor.
- [x] `/capabilities` informa modos, limites e indisponibilidade sem expor chaves.
- [x] Modo demo determinístico identificado como “Simulado — sem inferência LLM”.
- [x] Adaptador real migrado para `google-genai`, carregado sob demanda e com modelo em allowlist.
- [x] Consentimento obrigatório antes do processamento externo.
- [x] Rota provisória `POST /evaluation/upload` retorna JSON completo, sem sucesso por stream
  truncado.
- [x] Validação de mídia, arquivo vazio, tamanho, assinatura PDF, quantidade de páginas e ausência
  de texto extraível.
- [x] Erros explícitos para timeout de parsing, timeout do provedor, quota e falha do provedor.
- [x] Parser diferencia PDF inválido de PDF que requer OCR.
- [x] Parecer demo contém seis dimensões e não inventa nota final agregada.
- [x] Inferência real executada pelo mantenedor com fixture sintética e quota gratuita conferida:
  `gemini-3.5-flash-lite`, credencial principal, uso real e seis dimensões; sem fallback pago ou
  simulado.

## F1 — interface

- [x] Migração de Create React App para Vite sem recriar o projeto.
- [x] URL da API centralizada; nenhuma chave incluída no bundle público.
- [x] Seleção de arquivo separada da ação “Executar avaliação”.
- [x] Modos demo/real, limites e indisponibilidade apresentados na tela.
- [x] Confirmação explícita exibida antes de uma execução real.
- [x] Estados vazio, carregando, erro e concluído implementados.
- [x] Resultado simulado claramente marcado e exportável em JSON.
- [x] Capacidades futuras aparecem como “Planejado” sem links falsos.
- [x] Walkthrough visual realizado em desktop e viewport de 390 px, sem erro de página.
- [x] Fluxo F1 por teclado e mobile: mantenedor confirmou aprovação do runbook em 2026-09-13.

## Evidências automatizadas e operacionais

- [x] Imagens multi-stage e Compose para runtime, desenvolvimento e testes.
- [x] Comando agregado offline passou em contêineres sem rede e sem credenciais.
- [x] CI de pull request e `main` configurada para reutilizar o comando local.
- [x] Smoke containerizado validou health, capabilities e entrega da SPA.
- [x] Ruff do backend: `ruff check app tests`.
- [x] Backend: 111 testes passando, incluindo contratos, PostgreSQL, worker, buscas, judge,
  proveniência, baselines PDF/CSV/JSON e adaptador Gemini exercitado com cliente falso.
- [x] Frontend: typecheck e ESLint passando.
- [x] Frontend: 17 testes passando em 4 arquivos.
- [x] Build de produção Vite concluído.
- [x] Smoke HTTP em loopback para health, capabilities, CORS, upload demo, busca lexical, insight
  e judge separado.
- [x] Upload demo no navegador exibiu seis dimensões.
- [x] Exportação inspecionada com `simulated: true` e identificação textual de simulação.
- [x] `git diff --check` sem erro de whitespace.
- [x] Ruff do produto configurado com regras E/W/F; notebooks históricos e tooling de agentes
  fora do produto estão excluídos.

## Critérios de aceite da especificação

- [x] AC-001 — instalação, health, SPA e walkthrough demo na fatia F1.
- [x] AC-013 — suíte offline e isolamento dos testes reais validados até o EV-03.
- [x] AC-002 — resultado, histórico persistente e exportação identificam a simulação.
- [x] AC-003 — smoke real opt-in passou com modelo e consumo registrados; ausência de chave, quota
  e modelo indisponível têm falhas explícitas sem substituição por demo.
- [x] AC-004 — erros da rota e resultado estruturado inválido não são publicados como sucesso.
- [x] AC-005 — domínio/caso de uso e adaptadores demo/Gemini são testáveis sem rede.
- [ ] AC-006 — F4a cobre páginas PDF, F4b tabelas PDF e F4c CSV/JSON nativos; OCR executável e
  integração persistente dos formatos permanecem pendentes.
- [ ] AC-008 — testes de componente passaram; busca e insights passaram no walkthrough visual e
  mobile, mas comparação/impressão e avisos de extração ainda requerem o walkthrough ampliado.
- [ ] AC-014 — controles iniciais passaram; persistência e fases futuras exigem nova revisão.
- [ ] AC-010 — schema/rubrica estão validados; falta qualidade semântica com corpus e revisão humana.
- [x] AC-007 — persistência, reload, reexecução explícita e reinício real do worker passaram.
- [x] AC-012 — configuração, consumo, comparação e exportações de runs passaram na automação.
- [x] AC-009 — baselines lexical/vetorial, perfil opt-in e ausência de fallback silencioso validados.
- [ ] AC-011 e AC-015 — fases posteriores ainda não entregues.

## Situação consolidada

O mantenedor aprovou as etapas offline do runbook e executou a seção 11 com a fixture sintética em
2026-09-13. O smoke real usou `gemini-3.5-flash-lite`, credencial principal, 272 tokens de entrada,
880 de saída e retornou exatamente seis dimensões. A F2, a validação real e a implementação
automatizada da F3, as F4a–F4c e EV-01/EV-02 estão concluídos. O EV-03 passou na automação integrada
e no walkthrough visual; aguarda somente o teste real opt-in. Permanece também o walkthrough das
telas antigas.

- [x] Definir e implementar o schema interno F2a: revisão, unidades, dimensões e insuficiência.
- [x] Extrair unidades por página física com IDs determinísticos e hash da revisão.
- [x] Validar seis dimensões, notas, insuficiência e referências; renderizar Markdown no núcleo.
- [x] F2b: conectar contratos ao caso de uso, adaptadores demo/Gemini e resposta HTTP, incluindo
  rejeição de JSON inválido e renderização derivada na rota pública.
- [x] Expor `document.units` sem texto e `report` estruturado de modo aditivo na rota provisória.
- [x] Repetir no runbook a inspeção do contrato F2b; o smoke real validou modo, provedor, modelo,
  uso, slot de credencial e seis dimensões.
- [x] Persistir documentos e runs e executar avaliações no worker local.

## F3a — PostgreSQL e documentos persistidos

- [x] Registrar a substituição de SQLite por PostgreSQL antes de criar dados persistidos.
- [x] Adicionar PostgreSQL 17.11 ao Compose sem publicar porta no host.
- [x] Versionar e testar a migração inicial de documentos e unidades.
- [x] Implementar criação idempotente, listagem, consulta e inspeção de unidades em `/api/v1`.
- [x] Preservar a rota provisória de avaliação e o boot sem credenciais de provedor.
- [x] Implementar runs persistidos e worker na F3b.
- [x] Migrar a interface para documentos/runs na F3c.

## F3b — runs persistidos e worker local

- [x] Versionar a migração de runs com integridade de estados e resultados.
- [x] Criar e consultar runs em `/api/v1`, com idempotência e resultado apenas após sucesso.
- [x] Exigir consentimento e capacidade disponível antes de enfileirar uma avaliação real.
- [x] Reivindicar uma tarefa por vez com bloqueio PostgreSQL e persistir resultado ou erro seguro.
- [x] Marcar runs abandonados em `running` como `interrupted` no início do worker.
- [x] Validar o fluxo documento → run → worker → resultado no smoke offline da stack.
- [x] Migrar a tela, implementar reexecução explícita e reabrir resultados após reload na F3c.

## F3c — interface persistente e histórico recente

- [x] Trocar a rota em memória por admissão de documento e criação idempotente de run.
- [x] Exibir `queued`, `running`, `succeeded`, `failed` e `interrupted` sem progresso fictício.
- [x] Reabrir uma execução por `?run=<id>` após reload.
- [x] Listar até dez runs recentes na tela, identificando modo simulado/real e estado.
- [x] Reexecutar falha/interrupção explicitamente como novo run; modo real exige nova confirmação.
- [x] Exportar documento, configuração, consumo, parecer e Markdown sem texto extraído ou segredos.
- [x] Validar contratos e componentes na suíte containerizada: 56 testes backend e 3 frontend.
- [ ] Executar walkthrough visual, mobile e por teclado da nova tela em navegador.

## F3d — comparação, exportação e recuperação operacional

- [x] Ensaiar parada/reinício do worker com run em andamento.
- [x] Implementar comparação controlada de dois runs do mesmo documento.
- [x] Adicionar exportação Markdown/impressão além do JSON estruturado.
- [x] Documentar e testar backup/restauração do PostgreSQL local.
- [x] Impedir restore sem confirmação textual e sobrescrita silenciosa de backup.
- [ ] Executar walkthrough visual/mobile/teclado das telas F3c/F3d.

## F4a — qualidade de extração por página

- [x] Classificar cada página como `extracted`, `ocr_candidate` ou `no_text`, sem confundir ausência
  de texto com vazio ou ilegibilidade.
- [x] Persistir número físico, caracteres e presença de imagem raster por página.
- [x] Expor `GET /api/v1/documents/{id}/pages` e validar o contrato no smoke.
- [x] Exibir extração completa/parcial e páginas sinalizadas na avaliação.
- [x] Validar fixtures digital, somente imagem, em branco e mista sem rede nem OCR implícito.
- [ ] Executar walkthrough visual da advertência de qualidade em navegador.

## F4b — baseline tabular comparativo

- [x] Gerar em código uma fixture tabular sintética com zero, travessão e célula vazia.
- [x] Comparar cobertura literal do `pypdf` e exact match de células do `pdfplumber`.
- [x] Preservar página, linha, coluna e a distinção entre ausência, zero e travessão.
- [x] Manter o candidato exclusivamente no grupo de desenvolvimento/teste.
- [x] Registrar ambiente, resultado, limitações e decisão no
  [relatório do baseline tabular](../quality/pdf-table-extraction-baseline.md).

## F4c — baseline nativo de CSV/JSON

- [x] Definir e implementar localizadores e tipos escalares para CSV/JSON.
- [x] Validar fixtures e falhas de contrato sem rede ou LLM.
- [x] Registrar resultado e limitações sem anunciar suporte nos endpoints.

## Entregável de valor concluído — EV-01

**Resultado:** o usuário encontra evidências em uma dissertação persistida e abre trechos com página
e origem, sem LLM ou embedding.

- [x] Especificar consulta, filtros, ordenação e respostas vazia/erro da busca lexical.
- [x] Implementar endpoint de busca limitado a uma revisão autorizada.
- [x] Implementar a área “Busca” com consulta, trechos e páginas reais.
- [x] Validar fixture anotada, teclado, viewport estreita e indisponibilidade do banco.
- [x] Demonstrar PDF → busca → evidência e registrar a evidência de aceite.

## Entregável de valor concluído — EV-02

- [x] Implementar pgvector, embeddings E5 locais e índice reconstruível por revisão/perfil.
- [x] Diferenciar capacidades e respostas lexical/vetorial sem fallback silencioso.
- [x] Comparar os dois modos na interface e desabilitar o perfil indisponível.
- [x] Validar fixture anotada, custo local, reutilização, desktop, mobile e acessibilidade.

## Entregável de valor em validação — EV-03

- [x] Registrar system design e especificação rastreável próprios.
- [x] Implementar fila persistente, endpoint idempotente e worker sem misturar `evaluation_runs`.
- [x] Congelar pergunta, revisão, perfil, unidade, página, trecho e score antes da geração.
- [x] Implementar adaptadores demo/Gemini e rejeitar citações fora de `E1..En`.
- [x] Implementar tela, polling, histórico e exportações JSON/Markdown.
- [x] Validar no host: Ruff, 92 testes backend sem banco/live, ESLint, typecheck, 15 testes
  frontend e build Vite.
- [x] Executar migração/teste PostgreSQL, smoke Compose atualizado e backup/restore em Docker.
- [x] Executar walkthrough visual e mobile da tela `/insights`: criação, histórico, resposta,
  evidência e exportações passaram sem erros da aplicação ou violações detectadas pelo axe-core.
- [ ] Executar teste real opt-in do insight com documento sintético autorizado.

## Entregáveis seguintes

- [ ] EV-04 — ampliar formatos conforme demanda: integração CSV/JSON ou OCR de PDF.
- [ ] EV-05 — concluir qualidade semântica e revisão humana do judge; os modos demo e real opt-in
  estão implementados e cobertos sem rede.
- [ ] EV-06 — versão demonstrável, reproduzível e preparada tecnicamente para registro.

## Implementação funcional — EV-05

- [x] Registrar system design e especificação rastreável próprios.
- [x] Congelar o parecer fonte, seu hash e exatamente os trechos citados antes de enfileirar.
- [x] Persistir fila, estados, idempotência e resultado sem alterar `evaluation_runs`.
- [x] Validar dimensões e evidências dos achados contra o snapshot.
- [x] Integrar worker demo e Gemini com modelo distinto, saída estruturada e failover só por quota.
- [x] Exigir consentimento e configuração válida antes de enfileirar o modo real.
- [x] Executar, acompanhar e exportar o judge na tela de avaliação.
- [x] Validar PostgreSQL, API, componente, smoke, backup/restore e reinício do worker.
- [ ] Executar smoke real opt-in com fixture autorizada e quota conferida.
- [ ] Validar qualidade semântica com corpus autorizado e amostra humana.
