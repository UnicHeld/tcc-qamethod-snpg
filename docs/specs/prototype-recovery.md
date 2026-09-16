# Roteiro de recuperação e evolução do protótipo QA Method

- Status: `em-implementacao` — F0, F1, F2, F3a–F3d, F4a–F4c e EV-01/EV-02 da F5
  validados; EV-03 passou na automação integrada e no walkthrough visual e aguarda o teste real
  opt-in.
- Responsável: a definir com o mantenedor.
- Última atualização: 2026-09-16.
- System design: [recuperação do protótipo](../architecture/prototype-recovery-design.md).
- Decisões relacionadas: [execução e testes com Compose](../decisions/containerized-development-and-testing.md), além do
  [arquivamento dos notebooks da POC](../decisions/archive-poc-notebooks.md), da
  [persistência PostgreSQL](../decisions/postgresql-local-persistence.md) e do
  [failover de credenciais Gemini](../decisions/gemini-credential-failover.md).
- Acompanhamento: [checklist da recuperação](../operations/prototype-recovery-checklist.md).
- Validação reproduzível: [roteiro de testes](../operations/prototype-recovery-test-plan.md).
- Prioridade confirmada: melhorar o projeto existente, testar capacidades e preparar documentação
  para registro de software. SaaS fica para outra etapa.

## Contexto e problema

No baseline, o backend não tinha manifesto próprio preenchido, usava Gemini/SDK legado e não
integrava RAG ao avaliador web. A interface tinha um fluxo básico de upload/stream e cartões de
capacidades ainda não implementadas; não foram encontrados testes da aplicação. A fatia F1 já
corrigiu parte desse estado. A evidência detalhada e o ambiente observado estão no
[system design](../architecture/prototype-recovery-design.md).

Instalar todas as dependências antigas da raiz não é um plano suficiente de recuperação. É
necessário separar ambiente do serviço, corrigir contratos/erros, substituir integrações obsoletas
e validar uma fatia funcional antes de expandir recursos.

## Objetivo

Entregar um laboratório local de análise documental que outra pessoa consiga instalar, abrir e
demonstrar com dados autorizados, sem contratar serviços. Com credencial e quota gratuita disponíveis,
executar avaliação real, inspecionar evidências e comparar extração, recuperação e judge.

Três marcos diferentes devem ficar explícitos:

| Marco | Resultado | O que não comprova |
|---|---|---|
| M1 — retomada | API + interface + PDF digital + demonstração; caminho de LLM real disponível | Mock não comprova qualidade; teste real ainda depende de conta |
| M2 — laboratório | Documentos, histórico, busca e judge experimentais com evidências | Não equivale a produto público ou validação estatística do método |
| M3 — versão documentada | Build reproduzível, testes, manual e pacote técnico da versão | Não equivale a registro concedido ou titularidade resolvida |

## Escopo

### Incluído

- FastAPI/Python e React/TypeScript existentes, com atualização controlada de dependências.
- Modo de demonstração sem chave e modo de inferência real por free tier, sem cobrança automática.
- PDF digital primeiro; OCR seletivo e CSV/JSON como primeiros experimentos adicionais.
- Extração verificável, avaliação das seis dimensões e judge separado do parecer.
- Busca lexical e experimento RAG com PostgreSQL/pgvector e embeddings locais, sem conta paga
  obrigatória nem banco vetorial separado.
- Interface consistente, histórico, inspeção de evidências, comparação e exportação local.
- Testes automatizados offline, testes reais opt-in e preparação técnica para registro.
- Preservação dos notebooks apenas como histórico, sem migração, execução ou dependência do produto.

### Excluído

SaaS, usuários/organizações remotos, planos, pagamentos, operação pública, alta disponibilidade,
migração de toda a stack, grafos, chat genérico, agentes autônomos e instalação de todos os modelos
do catálogo. DOCX/XLSX e parsers especializados ficam no backlog opcional após PDF e CSV/JSON.
Não há autorização neste roteiro para contratar, publicar, registrar, assinar cessão, escolher
licença ou fazer commit/push.

## Requisitos

- **REQ-001:** instalar e inicializar API/interface em ambiente isolado e reproduzível por Compose,
  sem depender das bibliotecas de notebooks, runtimes do host ou credenciais no perfil padrão.
- **REQ-002:** distinguir modos simulado e real em configuração, interface, resultados e exportação.
- **REQ-003:** permitir inferência real por adaptador atualizado e modelo configurável elegível a
  teste gratuito, com confirmação de envio externo e falha explícita por ausência de chave/quota.
- **REQ-004:** validar entrada e propagar erros do parser/modelo corretamente, sem sucesso vazio.
- **REQ-005:** separar regras do método, casos de uso e clientes externos, com contratos testáveis.
- **REQ-006:** extrair unidades com localizadores, diferenciar fatos de sínteses e validar campos;
  OCR e formatos extras devem ser opcionais e explicitamente identificados.
- **REQ-007:** persistir revisões, tarefas e resultados locais; permitir consultar após reload e
  recuperar estados interrompidos sem reexecutar LLM silenciosamente.
- **REQ-008:** oferecer laboratório visual com navegação, estados claros, evidências e ações
  acessíveis; capacidades não implementadas não se apresentam como disponíveis.
- **REQ-009:** consultar evidências por busca lexical e perfil vetorial local opcional, identificando
  se uma avaliação usou documento direto ou RAG.
- **REQ-010:** produzir parecer validado nas seis dimensões, com justificativas/evidências e estado
  explícito de insuficiência; não gerar nota agregada não prevista no método.
- **REQ-011:** executar judge sobre um parecer existente, com rubrica e evidências, sem substituir
  o original ou se apresentar como validação humana definitiva.
- **REQ-012:** comparar execuções com configurações/versionamento registrados e exportar dados
  estruturados, distinguindo custo estimado, consumo real e resultado simulado.
- **REQ-013:** executar por contêiner testes essenciais de backend, interface e integração local
  sem rede/chaves; testes de provedores reais são opt-in e separados da CI comum.
- **REQ-014:** limitar execução ao ambiente local e proteger arquivos/segredos, sem fallback pago
  ou transferência externa não autorizada.
- **REQ-015:** entregar documentação operacional reconciliada, inventário de dependências/licenças
  e checklist técnico de versão para preparação do registro.

## Critérios de aceite

- **AC-001 / REQ-001:** em ambiente com Docker/Compose, construir por versões fixadas e abrir
  `/health`, interface e demonstração sem instalar Python/Node nem configurar Google, OpenAI ou
  uma capacidade vetorial.
- **AC-002 / REQ-002:** executar uma fixture em modo demo e encontrar a marcação “Simulado — sem
  inferência LLM” na tela, no histórico e no arquivo exportado.
- **AC-003 / REQ-003:** com conta elegível e consentimento, executar um documento autorizado e
  registrar modelo/consumo real; sem chave ou com quota indisponível, explicar o impedimento sem
  habilitar cobrança nem substituir a resposta por mock.
- **AC-004 / REQ-004:** entrada inválida, arquivo excessivo, PDF ilegível, timeout, JSON malformado
  e erro durante geração terminam com estado/código adequados, não resultado de sucesso vazio.
- **AC-005 / REQ-005:** testar regra da rubrica e caso de uso com adaptadores falsos, sem importar
  clientes externos no domínio nem inicializar SDK por import de router.
- **AC-006 / REQ-006:** em fixtures digital, escaneada e tabular, validar localizadores, ausência
  versus zero e estados de ilegibilidade; com OCR desabilitado, pedir habilitação em vez de inventar texto.
- **AC-007 / REQ-007:** recarregar a tela e reabrir um resultado; encerrar/reiniciar o worker e
  encontrar a tarefa abandonada como interrompida, com reexecução explícita e novo ID.
- **AC-008 / REQ-008:** concluir upload → configuração → execução → evidência → exportação com
  teclado; verificar estados vazio, erro e carregamento em desktop e viewport estreita.
- **AC-009 / REQ-009:** uma consulta de fixture recupera a unidade anotada; os perfis lexical e
  vetorial são diferenciados e indisponibilidade de pgvector não impede avaliação direta/demo.
- **AC-010 / REQ-010:** relatório contém exatamente as seis dimensões definidas, notas no intervalo
  permitido ou insuficiência explícita, citações válidas e nenhuma nota final agregada inventada.
- **AC-011 / REQ-011:** judge recebe parecer congelado com erro inserido para teste e publica achado
  rastreável em relatório separado; o parecer original permanece inalterado.
- **AC-012 / REQ-012:** comparar dois runs do mesmo documento/revisão e exportar configuração,
  resultados, duração e consumo; divergências de modo/modelo/rubrica são visíveis.
- **AC-013 / REQ-013:** o comando containerizado único executa lint, typecheck, testes unitários,
  de contrato/componente, builds e smoke local sem credenciais; a suíte real não é executada por
  padrão nem produz custo na CI comum.
- **AC-014 / REQ-014:** conferir bind local, CORS explícito, limites, destinos de arquivos e ausência
  de segredos no bundle/log/exportação; negar chamada externa sem consentimento.
- **AC-015 / REQ-015:** seguir o manual a partir de ambiente novo e restaurar backup de teste;
  reunir pacote técnico identificado por versão/hash e registrar pendências de autoria/licenças.

## Contratos e dados

Os objetos, ownership, endpoints e transição da rota legada são definidos no
[system design](../architecture/prototype-recovery-design.md). Antes de cada fase que altera API,
detalhar seus schemas OpenAPI/Pydantic, códigos de erro e fixtures. Nenhum endpoint proposto deve
ser tratado como já disponível. Usar IDs de revisão/run, não nomes de arquivo como identidade.

Defaults iniciais propostos para a especificação detalhada: upload de até 20 MiB e 300 páginas,
um run pesado ativo, timeout de parsing de 60 segundos e de chamada LLM de 180 segundos. Limites
configuráveis no backend e visíveis na UI; calibrar em fixture/hardware antes de adotá-los.
Arquivo maior não deve ser cortado silenciosamente: apresentar impedimento ou modo segmentado.

### Contrato de retomada (F1)

Durante F1, a rota legada `POST /evaluation/upload` permanece disponível, mas passa a responder
JSON completo em vez de texto em streaming. A requisição multipart recebe `file`, `mode` (`demo`
ou `real`) e `confirm_external_processing`; o último campo deve ser verdadeiro para `real`.
A resposta registra modo, simulação, provedor/modelo, metadados da extração, Markdown e consumo.

`GET /health` verifica apenas o processo. `GET /capabilities` informa limites e disponibilidade
dos modos sem expor credenciais. Falhas HTTP usam `detail.code` e `detail.message`; os códigos
iniciais são `unsupported_media_type`, `empty_file`, `file_too_large`, `invalid_pdf`,
`page_limit_exceeded`, `pdf_without_text`, `parse_timeout`,
`external_processing_not_confirmed`, `provider_unavailable`, `provider_quota_exceeded`,
`provider_timeout` e `provider_error`. O frontend deve mostrar a mensagem e não converter falha
em resultado parcial. A futura API de documentos/runs substituirá este contrato provisório em F3.

Manter resultados estruturados e Markdown derivado. IDs de evidências devem existir na revisão;
campos desconhecidos não são inferidos para completar schema. Exportações devem incluir versões
e marcação de simulação, mas não chaves, caminhos privados ou o PDF original por padrão.

## Segurança e confiabilidade

Um operador local não elimina risco de PDF malicioso, prompt injection ou dados pessoais. Manter
validações, limites e separação entre conteúdo do documento e instruções do método. A simulação
deve testar também essas barreiras. Credenciais são configuradas no backend; a interface apenas
consulta disponibilidade e solicita execução autorizada.

Gratuidade deve ser confirmada no plano da conta, não inferida pelo nome do modelo. O modo de
baixo custo precisa de allowlist de provedores/modelos autorizados e bloqueio de ferramentas pagas.
O backend não consegue garantir preço zero se a própria conta externa estiver configurada para
cobrar; conferir console e política de faturamento antes do teste real. Quota acaba → execução
para, com orientação para tentar depois ou escolher explicitamente outra modalidade permitida.

## Plano de implementação

### Roadmap por entregáveis de valor

As fases F0–F7 permanecem como rastreabilidade técnica. A ordem do trabalho restante passa a ser
guiada pelos entregáveis abaixo; concluir um componente isolado não conclui um entregável.

| ID | Entregável | Valor demonstrável | Fases/requisitos relacionados |
|---|---|---|---|
| EV-01 | Encontrar evidências no próprio documento | O usuário pesquisa uma dissertação já admitida e abre trechos com página e origem, sem depender de LLM | F5; REQ-009, REQ-013 |
| EV-02 | Encontrar conteúdo semanticamente relacionado | O usuário alterna busca lexical/vetorial, compara resultados e mantém a busca lexical se pgvector estiver indisponível | F5; REQ-009, REQ-012–014 |
| EV-03 | Gerar insights RAG rastreáveis | O usuário faz uma pergunta e recebe resposta baseada apenas no pacote recuperado, com citações e exportação | F5; REQ-002–005, REQ-009, REQ-012–014 |
| EV-04 | Analisar documentos hoje não cobertos | O usuário admite formatos priorizados ou PDF escaneado e inspeciona qualidade/localizadores antes de avaliar | F4; REQ-004–006, REQ-013–014 |
| EV-05 | Verificar e comparar pareceres | O usuário executa judge separado, abre achados e compara runs sem alterar o parecer original | F6; REQ-010–013 |
| EV-06 | Demonstrar e preservar uma versão | Outra pessoa instala, executa o fluxo, restaura backup e confere o pacote técnico sem conhecimento tácito | F7; REQ-001, REQ-013–015 |

#### EV-01 — encontrar evidências no próprio documento

- **Status:** concluído e validado em 2026-09-15.

- **Demonstração:** admitir um PDF sintético, pesquisar uma expressão e abrir os resultados que
  apontam para unidades e páginas reais.
- **Pronto quando:** existir busca lexical por documento, com consulta, filtros, ordenação
  determinística, estado vazio/erro, endpoint e tela; fixture anotada comprovar o resultado esperado.
- **Limites:** não gera resposta, não usa embedding e não promete relevância semântica.

Contrato do EV-01:

- `POST /api/v1/search` recebe JSON com `document_id`, `query` e `limit` opcional, padrão 10;
- `query` é aparada e deve conter de 1 a 200 caracteres; `limit` aceita de 1 a 20;
- a busca usa somente unidades da revisão indicada e o índice textual do PostgreSQL em português;
- a resposta identifica `retrieval_mode: "lexical"`, consulta normalizada, documento e hits com
  `unit_id`, página, trecho de texto simples e score de ordenação;
- hits são ordenados por score decrescente e, em empate, página e ID crescentes;
- nenhum resultado retorna HTTP 200 com `hits` vazio; documento inexistente retorna
  `document_not_found`, consulta vazia retorna `invalid_search_query` e falha do banco retorna
  `database_unavailable`;
- trechos têm no máximo 320 caracteres, não contêm HTML de destaque e o score é apresentado apenas
  como relevância lexical, nunca como confiança ou probabilidade de verdade;
- a consulta e os hits não são persistidos nesta entrega; logs não incluem texto documental.

#### EV-02 — encontrar conteúdo semanticamente relacionado

- **Status:** concluído e validado em 2026-09-15.
- **Demonstração:** executar a mesma consulta nos modos lexical e vetorial e inspecionar diferenças,
  modelo de embedding e fontes recuperadas.
- **Pronto quando:** PostgreSQL + pgvector, embeddings locais versionados e índice reconstruível
  estiverem integrados; indisponibilidade vetorial deixar EV-01 funcional; qualidade e custo local
  estiverem medidos em fixture anotada.
- **Limites:** score vetorial não é probabilidade de verdade e ainda não há texto gerado.

Contrato do EV-02:

- `POST /api/v1/search` aceita `retrieval_mode: "lexical" | "vector"`, mantendo `lexical` como
  padrão compatível; consulta, documento e limite conservam as validações do EV-01;
- a resposta vetorial informa `embedding_model`, `embedding_dimension` e `chunk_version`; esses
  campos são nulos no modo lexical;
- o perfil inicial usa `intfloat/multilingual-e5-small`, 384 dimensões, distância cosseno,
  prefixos E5 e chunks de até 384 tokens com sobreposição de 64 tokens;
- a primeira busca vetorial de uma revisão materializa, de forma atômica, embeddings derivados por
  unidade/chunk; execuções seguintes reutilizam o perfil, que pode ser apagado e reconstruído sem
  alterar documento ou unidades;
- hits continuam vinculados a `unit_id` e página reais, usam o texto do chunk como trecho e são
  ordenados por distância, página, índice do chunk e ID; score é relevância de ordenação;
- `GET /capabilities` diferencia busca lexical sempre disponível de busca vetorial opt-in e não
  inicializa nem baixa o modelo;
- modo vetorial desabilitado, extensão ausente, download/cache indisponível ou falha de inferência
  retornam `vector_search_unavailable` sem executar busca lexical silenciosamente;
- o perfil padrão e a suíte offline não baixam pesos. O operador habilita o perfil conscientemente;
  o primeiro uso requer rede, enquanto usos posteriores reutilizam o cache local.

Evidências do EV-02: testes de serviço, contrato e PostgreSQL cobrem indexação reconstruível,
reutilização, erros preservados e ausência de fallback silencioso. O smoke opt-in recuperou a
página anotada em top-1, mediu 44,907 s na primeira consulta e 0,034 s na reutilização, com cache de
273,6 MiB. Detalhes e limites estão no
[baseline vetorial](../quality/vector-search-baseline.md).

#### EV-03 — gerar insights RAG rastreáveis

- **Demonstração:** perguntar sobre uma dissertação, abrir cada evidência usada e exportar pergunta,
  configuração, resposta e referências.
- **Pronto quando:** recuperação congelada alimentar o adaptador demo/real, citações forem validadas
  contra a revisão e falhas não publicarem resposta parcial; comparação com leitura direta estiver
  disponível sem alterar simultaneamente a rubrica.
- **Limites:** não é chat aberto, validação humana definitiva ou autorização para enviar documentos
  a provedor externo sem consentimento.

#### EV-04 — analisar documentos hoje não cobertos

- **Demonstração:** admitir um formato priorizado, inspecionar seus localizadores/qualidade e decidir
  conscientemente se há material suficiente para avaliação.
- **Pronto quando:** demanda real escolher a próxima entrada; `DocumentUnit` e PostgreSQL suportarem
  localizadores discriminados; API/UI e exportação preservarem proveniência. O baseline CSV/JSON da
  F4c está pronto, mas sua integração compete com OCR de PDF conforme valor observado.
- **Limites:** não oferecer suporte universal, inferência silenciosa de tipos ou OCR implícito.

#### EV-05 — verificar e comparar pareceres

- **Demonstração:** congelar um parecer com erro controlado, executar judge e abrir o achado separado
  ao lado de outro run comparável.
- **Pronto quando:** judge, evidências, configuração e exportação forem persistidos separadamente;
  erros controlados tiverem cobertura e uma amostra humana distinguir teste funcional de qualidade.
- **Limites:** judge não corrige o original nem substitui banca ou revisão humana.

#### EV-06 — demonstrar e preservar uma versão

- **Demonstração:** uma pessoa parte de ambiente limpo, executa o fluxo aprovado e restaura um backup
  seguindo apenas o manual.
- **Pronto quando:** testes, walkthrough, documentação reconciliada, inventário de dependências e
  pacote técnico identificado por versão/hash estiverem aprovados pelo mantenedor.
- **Limites:** não inclui publicação, protocolo de registro, escolha de licença, commit ou tag sem
  autorização explícita.

**Entregável corrente: EV-03.** O código congela a recuperação como entrada de uma geração RAG
citável sem alterar a rubrica. PostgreSQL, Compose, smoke e backup/restore passaram; a promoção
final depende do walkthrough visual e do teste real opt-in da [especificação própria](rag-insights.md).

### Visão geral e dependências

| Fase | Entrega | Dependência | Esforço indicativo |
|---|---|---|---|
| F0 | Inventário e baseline protegido | Nenhuma | 0,5–1 dia-pessoa |
| F1 | API e interface voltam a rodar; demo e adaptador real | F0 | 2–4 dias-pessoa |
| F2 | Contratos e separação modular do fluxo existente | F1 | 2–3 dias-pessoa |
| F3 | Histórico, tarefas e laboratório visual | F2 | 3–5 dias-pessoa |
| F4 | Extração melhor e formatos experimentais | F2; integrar UI sobre F3 | 3–5 dias-pessoa |
| F5 | Busca/RAG local, opcional | F3 + F4 | 2–4 dias-pessoa |
| F6 | Judge e comparação controlada | F3 + F4; RAG depende de F5 | 2–4 dias-pessoa |
| F7 | Estabilização, documentação e pacote de versão | F1–F6 no escopo aprovado | 1–2 dias-pessoa |

Total indicativo: **15,5–28 dias-pessoa**, aproximadamente 3–6 semanas de dedicação integral de uma
pessoa experiente, sem contar espera por anotadores, quotas, revisão institucional ou registro.
É estimativa de planejamento, não prazo contratado. IA local pesada, novos formatos e agentes
podem ser cortados sem impedir a versão principal. Não somar automaticamente às estimativas dos
estudos de SaaS, cujo escopo é diferente.

### F0 — fotografar o estado e isolar o ambiente

Requisitos: REQ-001, REQ-013, REQ-014, REQ-015.

1. Registrar `git status`, inventário dos módulos, versões e comandos de baseline. Preservar
   mudanças locais; notebooks são arquivo histórico e não devem ser executados ou migrados.
2. Identificar dependências diretas efetivamente importadas pela API/interface e separar as de
   pesquisa. Confirmar Python 3.12 disponível em ambiente dedicado; não instalar os pins antigos
   no Python 3.14 global encontrado na inspeção.
3. Inspecionar manifests/lock e varrer referências obsoletas; documentar erros de instalação/build
   efetivamente observados quando esses comandos forem executados.
4. Preparar fixtures sintéticas pequenas: PDF digital, PDF sem texto, PDF inválido, CSV/JSON e
   resultados simulados válidos/inválidos. Gerar PDFs de teste ou criar exceção pontual de ignore,
   pois o `.gitignore` atual ignora PDFs; não liberar documentos reais em massa.
5. Definir arquivos de configuração documentados, diretório de runtime ignorado e checklist de
   segredos/licenças. Qualquer chave exposta deverá ser tratada pelo responsável, sem reproduzi-la
   em relatório e sem reescrever histórico automaticamente.
6. Criar imagens multi-stage e Compose para runtime, desenvolvimento e testes, mantendo o perfil
   demo offline e os serviços futuros fora do perfil padrão até terem uso e healthcheck reais.

Saída: baseline registrado, fixtures autorizadas e plano de dependências. Não afirmar que o
projeto roda apenas porque Python/Node respondem `--version`.

### F1 — recuperar a fatia vertical, antes de expandir funcionalidades

Requisitos: REQ-001–004, REQ-013, REQ-014.

Backend:

- Preencher manifesto mínimo e resolução fixada do serviço, com teste/lint separados. Configurar
  Ruff E/W/F e pytest; verificar dependências multipart/PDF/FastAPI e suas compatibilidades.
- Centralizar settings, criar dependências sob demanda e garantir boot sem credencial. Liveness
  não deve executar uma chamada LLM. Corrigir o nome `EvalationService` com referências/testes.
- Substituir `google-generativeai` por `google-genai` no adaptador ativo e tornar o modelo
  configurável. O Google documenta a migração de SDK; a escolha do ID depende da conta e do teste.
  [Guia oficial de migração](https://ai.google.dev/gemini-api/docs/migrate).
- Implementar mock determinístico no mesmo contrato do adaptador real. Separar falha de validação
  de HTTP 500; não engolir erro de geração ou publicar stream truncado como sucesso.
- Validar bytes/formato/tamanho e detectar PDF sem texto; nesta fase OCR pode apenas aparecer como
  necessidade explícita, sem bloquear a demonstração de PDF digital.
- Executar os testes do backend e frontend em targets próprios sem rede, agregar um smoke test da
  topologia e reutilizar o mesmo comando na CI.

Frontend:

- Migrar CRA para Vite preservando React/Router/Tailwind e as duas rotas existentes. Atualizar
  entrypoint, scripts, TypeScript e configuração de assets; não gerar novo projeto sobre arquivos
  existentes nem copiar template por cima do trabalho local.
- Fixar Node/npm suportados e atualizar o lock de forma controlada. Corrigir dependências diretas:
  `react-icons` é importado, mas hoje chega transitivamente via `@types/react-icons`; declarar a
  biblioteca usada e remover tipos redundantes quando confirmado. Revisar `@types/axios` também.
- Centralizar URL da API. Se usar Vite em porta diferente, atualizar CORS e documentação juntos.
  Nenhuma chave deve ir para variáveis públicas do frontend.
- Separar seleção de arquivo do botão “Executar”; mostrar modo, limites e confirmação de envio.
  Corrigir consumo de stream UTF-8 e falhas, ou usar resposta completa provisória com estados claros.

Gate M1: AC-001, AC-002, AC-004 e AC-014 passam offline; AC-003 tem teste real registrado ou
pendência explícita de credencial/quota. Demonstrar upload de PDF, extração e resultado. Se só
houver mock, registrar **“interface/contratos funcionando; inferência real ainda não validada”**.

### F2 — organizar a arquitetura existente com contratos

#### Fatia F2a — contratos internos e proveniência por página

Status: `validado`. Escopo: núcleo e parser; integração do parecer estruturado com
adaptadores/HTTP fica na F2b. Sem dependência nova, migração de dados ou alteração da rubrica.

- F2a-AC1 / REQ-006: parser preserva número físico de página e IDs determinísticos por hash;
  páginas vazias não deslocam localizadores.
- F2a-AC2 / REQ-005, REQ-010: contrato rejeita dimensões duplicadas/ausentes, campos desconhecidos,
  notas fora de 0–10/não finitas, insuficiência com nota e justificativas vazias.
- F2a-AC3 / REQ-006, REQ-010: referências inexistentes ou de outra revisão são rejeitadas; a
  renderização deriva seis seções ordenadas sem nota agregada e identifica simulação.
- F2a-AC4 / REQ-013: testes offline containerizados passam preservando o contrato público F1.

Não há decisão bloqueante para esses contratos internos: escala, seis dimensões e insuficiência
já estão previstas neste roteiro. Evidência sintaticamente válida não comprova suporte semântico
da afirmação; essa avaliação continua dependente de corpus e revisão humana.

Evidências: `tests/test_domain_evaluation.py` cobre os critérios F2a-AC1–3. Na conclusão da F2,
os testes de API, parser, domínio e avaliação continuam passando (39 testes backend no total), e
F2a-AC4 é verificado pelo comando containerizado de qualidade.

#### Fatia F2b — caso de uso, adaptadores e resposta pública

Status: `validado offline`. Escopo: conectar o contrato tipado da F2a à rota provisória e aos
adaptadores demo/Gemini, preservando os campos públicos da F1. Não há persistência nesta fatia.

- F2b-AC1 / REQ-005, REQ-010: demo e Gemini produzem o mesmo `EvaluationDraft`; o caso de uso
  valida exatamente as seis dimensões, notas/insuficiência e evidências antes de publicar sucesso.
- F2b-AC2 / REQ-005: Gemini solicita JSON conforme o schema, rejeita resposta vazia ou inválida e
  mantém falha de quota/provedor explícita, sem fallback para demo.
- F2b-AC3 / REQ-006, REQ-010: a resposta adiciona `document.units` sem texto e `report` tipado; o
  `result_markdown` é derivado do relatório validado, nunca tratado como fonte do resultado.
- F2b-AC4 / REQ-013: cliente Gemini falso comprova configuração, parsing e uso de tokens sem rede
  ou credencial; a suíte containerizada completa passa com o smoke da rota demo.

O contrato é aditivo: `mode`, `simulated`, provedor/modelo, versão do prompt, metadados, Markdown
e uso continuam presentes. `document.units` expõe somente ID determinístico e página física;
texto extraído não é devolvido. `report` registra hash da revisão, simulação, título, resumo e as
seis dimensões com justificativa, nota/insuficiência e IDs de evidência. A versão do prompt passa
a `qa-method-structured-v2`.

Evidências: `tests/test_evaluation_service.py` cobre demo, fábrica, JSON estruturado do Gemini,
resposta malformada e evidência de outra revisão; `tests/test_api.py` cobre o contrato aditivo e a
ausência de texto nas referências públicas. Em 2026-09-13, o mantenedor executou o smoke real com
fixture sintética: `gemini-3.5-flash-lite`, slot `primary`, uso real, 272 tokens de entrada, 880 de
saída e exatamente seis dimensões.

#### Implementação consolidada da F2

Requisitos: REQ-005, REQ-006, REQ-010, REQ-013.

1. Criar contratos de documento/unidade/evidência/parecer e interfaces pequenas para parser e LLM.
2. Retirar regra do método de clientes SDK e routers; preservar as seis dimensões e a omissão de
   identificação pessoal no parecer. Separar rubrica, instrução técnica e template de apresentação.
3. Tornar resultado tipado, com validação de notas, evidências e insuficiência. Definir schema de
   erro e impedir JSON inválido → objeto vazio → sucesso.
4. Adaptar os serviços existentes para esses contratos, com testes antes de mover arquivos.
5. Manter avaliação direta como baseline explícito, sem dizer que já usa RAG. Não acrescentar
   LangChain/LangGraph apenas para encapsular uma chamada fixa de modelo.

Saída alcançada: núcleo testável sem rede, adaptadores substituíveis e fixtures de relatórios
reais/simulados.
Gate: AC-005 e AC-010, sem regressão do M1. Alteração de rubrica além do contrato exige revisão
acadêmica; não é consequência automática da refatoração.

### F3 — histórico local e interface de laboratório

Requisitos: REQ-007, REQ-008, REQ-012, REQ-014.

1. Introduzir PostgreSQL local, armazenamento gerenciado e versionamento de schema. Persistir documentos,
   configurações e resultados com IDs estáveis; manter os dados de pesquisa existentes intactos.
2. Implementar run persistido e worker único conforme o design. Primeiro polling com progresso
   por estágio; porcentagem apenas quando houver medida real. Evitar “87%” fictício para LLM.
3. Migrar a tela da rota legada para run/endpoints versionados; reload deve reabrir o resultado.
4. Criar layout do laboratório descrito adiante, componentes compartilhados e estados acessíveis.
5. Exportar JSON e Markdown/relatório para impressão, sem adicionar gerador PDF pesado no primeiro
   momento. Excluir segredos e sinalizar conteúdo simulado em toda exportação.
6. Preparar backup/restauração local e encerramento limpo de worker; teste de reinício obrigatório.

#### Fatia F3a — fundação PostgreSQL e documentos

- F3a-AC1 / REQ-007: a stack cria e migra um PostgreSQL local sem serviço contratado; migrações são
  idempotentes e testadas em banco real no Compose.
- F3a-AC2 / REQ-006, REQ-007: `POST /api/v1/documents` valida/extrai PDF digital e persiste revisão e
  unidades; reenvio dos mesmos bytes retorna o mesmo documento sem duplicar unidades.
- F3a-AC3 / REQ-007, REQ-008: listar/consultar documentos e unidades funciona após nova conexão da
  API; a rota provisória de avaliação continua disponível.
- F3a-AC4 / REQ-014: banco não é publicado no host, respostas não contêm credenciais e testes não
  usam chave de provedor.

Runs persistidos, worker, migração da tela, exportação e backup/restauração permanecem nas próximas
fatias da F3; F3a não declara AC-007/008/012 completos.

Evidências da F3a: `tests/test_documents_api.py` cobre o contrato HTTP com reabertura e idempotência;
`tests/test_postgres_documents.py` executa duas vezes a migração e o repositório contra PostgreSQL
17.11 real. Em 2026-09-13, `./scripts/test-containers.sh` passou com Ruff, 44 testes backend,
typecheck, ESLint, Vitest, builds e smoke da stack incluindo a listagem persistente. O projeto e o
volume PostgreSQL de teste foram removidos ao final.

Gate: AC-007, AC-008, AC-012 e AC-014. O laboratório deve manter a avaliação básica utilizável
mesmo com busca, OCR e judge ainda indisponíveis.

#### Fatia F3b — runs persistidos e worker local

Status: `validado offline`.

Escopo: persistir solicitações de avaliação e executá-las fora do processo HTTP. A tela permanece
na rota provisória nesta fatia; sua migração será F3c. O worker processa uma tarefa por vez, usa o
mesmo código de avaliação e não retoma automaticamente chamadas LLM interrompidas.

- F3b-AC1 / REQ-007, REQ-012: `POST /api/v1/runs` cria uma avaliação `queued` para documento
  existente e `GET /api/v1/runs/{id}` expõe estado, configuração, timestamps e consumo. Uma mesma
  `Idempotency-Key` com a mesma solicitação retorna o mesmo run; reutilizá-la com parâmetros
  diferentes retorna conflito.
- F3b-AC2 / REQ-007: o worker reivindica runs com bloqueio PostgreSQL, transita
  `queued → running → succeeded|failed` e persiste parecer JSON/Markdown ou erro seguro. O resultado
  só fica disponível após sucesso.
- F3b-AC3 / REQ-007: ao iniciar, o worker marca runs deixados em `running` como `interrupted`; não
  reenvia automaticamente conteúdo ao provedor nem transforma interrupção em sucesso.
- F3b-AC4 / REQ-003, REQ-014: runs reais exigem consentimento e capacidade disponível no momento da
  submissão; credenciais nunca são persistidas. O slot usado, modelo, prompt e tokens são registrados.
- F3b-AC5 / REQ-013: repositório/worker têm testes offline e integração PostgreSQL; a rota legada
  continua funcionando, e o worker não faz chamada externa nos testes comuns.

F3b não conclui reload da interface, reexecução explícita, comparação/exportação de runs nem
backup/restauração. Esses itens permanecem para F3c/F3d antes de declarar AC-007/008/012 completos.

Evidências da F3b: `tests/test_runs_api.py` cobre submissão, idempotência, consentimento,
indisponibilidade do provedor, publicação do resultado e preflight CORS; `tests/test_run_worker.py`
cobre sucesso, reconciliação e configuração incompatível; `tests/test_postgres_runs.py` exercita a
fila e as transições contra PostgreSQL 17.11. Em 2026-09-14, `./scripts/test-containers.sh` passou
com Ruff, 55 testes backend, typecheck, ESLint, Vitest, builds e smoke completo de documento → run
→ worker → resultado, sem credenciais ou chamadas externas.

#### Fatia F3c — interface persistente e histórico recente

Status: `implementado e validado automaticamente`; walkthrough visual/teclado pendente.

Escopo: substituir na tela de avaliação a chamada provisória em memória pelo fluxo persistente da
F3a/F3b. A rota legada permanece disponível para compatibilidade nesta fatia. Comparação de runs,
exportação Markdown e backup/restauração continuam na F3d.

- F3c-AC1 / REQ-007, REQ-008: a tela admite o PDF em `/api/v1/documents`, cria o run com uma
  `Idempotency-Key` por intenção do usuário e acompanha `queued`/`running` por polling até um estado
  terminal, sem porcentagem fictícia.
- F3c-AC2 / REQ-007: `GET /api/v1/runs` lista até 100 execuções recentes, opcionalmente filtradas por
  documento, em ordem decrescente de criação. A tela permite abrir um item por `?run=<id>` e o
  restaura após reload consultando API e PostgreSQL, sem depender do resultado em memória.
- F3c-AC3 / REQ-007, REQ-014: runs `failed` e `interrupted` mostram código/mensagem seguros. Reexecutar
  é uma ação explícita, exige nova confirmação no modo real e cria um novo run/ID; nenhuma chamada
  externa é repetida automaticamente.
- F3c-AC4 / REQ-002, REQ-008, REQ-012: o resultado mostra simulação, documento, status, provedor,
  modelo, prompt, timestamps e consumo; a exportação JSON contém documento, run e parecer sem PDF,
  texto extraído, chave ou URL privada de banco.
- F3c-AC5 / REQ-013: testes de contrato e componente cobrem listagem, submissão, polling, reload,
  falha e reexecução; a suíte containerizada e o fluxo legado continuam passando sem credenciais.

O frontend trata `failed` e `interrupted` como estados concluídos sem resultado. `succeeded` só é
publicado depois de `GET /api/v1/runs/{id}/result` validar o parecer persistido. A lista recente é
um histórico operacional local, não paginação definitiva nem comparação científica.

Evidências da F3c: `tests/test_runs_api.py` cobre a listagem geral/por documento;
`Evaluation.test.tsx` cobre admissão, `Idempotency-Key`, polling até sucesso, reload por URL e
reexecução de run interrompido com novo ID. Em 2026-09-14, `./scripts/test-containers.sh` passou com
Ruff, 56 testes backend, 3 testes frontend, typecheck, ESLint, builds e smoke da listagem
persistente. O executável `agent-browser` e outro navegador local não estavam disponíveis, portanto
o walkthrough visual/teclado ampliado não foi declarado como aprovado.

#### Fatia F3d — comparação, exportação e recuperação operacional

Status: `implementado e validado automaticamente`; walkthrough visual/teclado pendente.

Escopo: concluir as capacidades operacionais da F3 sem criar novo formato persistido. A comparação
é derivada de dois runs já congelados; backup/restauração atua somente no PostgreSQL local e exige
confirmação explícita antes de substituir o estado corrente.

- F3d-AC1 / REQ-012: selecionar dois runs `succeeded` do mesmo documento mostra lado a lado ID,
  modo, provedor/modelo, prompt, timestamps, duração, consumo e as seis dimensões. Documentos
  diferentes são recusados e nenhum parecer é alterado.
- F3d-AC2 / REQ-002, REQ-012: um resultado pode ser exportado em JSON e Markdown ou enviado ao
  diálogo de impressão. Os artefatos identificam simulação e configuração, sem PDF, texto extraído,
  credenciais ou URL privada do banco.
- F3d-AC3 / REQ-007, REQ-015: `scripts/backup-postgres.sh` produz dump customizado por escrita
  temporária/atômica e não sobrescreve arquivo existente sem autorização explícita;
  `scripts/restore-postgres.sh` valida entrada e exige confirmação textual antes do restore limpo.
- F3d-AC4 / REQ-007, REQ-013: o smoke isolado cria backup, remove os dados apenas do volume de teste,
  restaura e comprova a contagem anterior. Em seguida inicia um run em `running`, reinicia o worker
  e observa `interrupted`, sem reexecutar a avaliação.
- F3d-AC5 / REQ-008, REQ-013: testes de componente cobrem comparação e exportação, e o comando
  containerizado único executa o smoke operacional sem rede ou credenciais externas.

A comparação nesta fatia é local e descritiva; não calcula vencedor ou significância. O restore é
destrutivo por natureza e por isso não possui fallback silencioso nem confirmação implícita.

Evidências da F3d: `runExport.test.ts` valida a identificação e configuração do Markdown;
`Evaluation.test.tsx` cobre a comparação de dois resultados congelados. O smoke operacional
`backup-restore-smoke.sh` usa somente um projeto `qa-method-test*`, comprova backup/restore pela
contagem de documentos e reinicia o worker com um run em andamento, observando `interrupted`. Em
2026-09-14, `./scripts/test-containers.sh` passou com 56 testes backend, 5 frontend, builds, smoke
HTTP e smoke operacional. A verificação visual permaneceu pendente porque `agent-browser` e
navegadores locais não estavam disponíveis.

### F4 — melhorar extração antes de trocar modelos em massa

Requisitos: REQ-004, REQ-006, REQ-013.

#### Fatia F4a — qualidade de extração por página

Status: `implementado e validado automaticamente`; walkthrough visual pendente.

Esta fatia adiciona um contrato conservador ao baseline pypdf existente, sem executar OCR nem
inferir conteúdo ausente:

- cada página física recebe exatamente um estado `extracted`, `ocr_candidate` ou `no_text`;
- `extracted` exige texto não vazio; `ocr_candidate` significa ausência de texto e presença de ao
  menos uma imagem raster detectável; `no_text` significa apenas que texto e imagem raster não
  foram detectados, sem afirmar que a página está semanticamente vazia;
- quantidade de caracteres e sinal de imagem são persistidos por página e reabertos pela API;
- PDFs inteiramente sem texto continuam recusados; a mensagem diferencia quando há páginas
  candidatas a OCR, e OCR não é iniciado implicitamente;
- a interface mostra advertência e páginas afetadas ao lado dos metadados do documento, sem
  transformar ausência de texto em nota, zero ou execução bem-sucedida de OCR.

Critérios da F4a:

- F4a-AC1 / REQ-006: PDFs digital e misto produzem classificações determinísticas em fixtures
  sintéticas, preservando número físico e hash; PDF somente com imagem produz erro explícito de
  candidato a OCR, pois documentos inteiramente sem texto não são admitidos.
- F4a-AC2 / REQ-004: documento sem qualquer texto retorna erro explícito e informa se OCR seria
  necessário; o perfil padrão não chama OCR, rede ou LLM.
- F4a-AC3 / REQ-006, REQ-013: `GET /api/v1/documents/{id}/pages` reabre a classificação persistida
  e o frontend apresenta a limitação; migração, repositório, rota e componente têm testes offline.

Extração estruturada de tabelas e CSV/JSON foram separadas nas F4b/F4c. Docling e OCR seletivo
permanecem posteriores, o que permite medir uma alteração por vez sem introduzir várias
dependências nesta fatia.

#### Fatia F4b — baseline tabular comparativo

Status: `validado offline`.

Esta fatia cria um experimento offline reproduzível antes de escolher outro parser de produção:

- `pdfplumber` entra somente no grupo de desenvolvimento/teste e não no target de runtime;
- uma fixture PDF sintética contém grade, cabeçalhos, valores literais, zero, travessão e célula
  vazia, sem dados pessoais;
- o pypdf continua sendo o baseline de texto; o candidato extrai células com página, linha e coluna,
  preservando `None`, `0` e `—` como valores distintos;
- o teste mede cobertura literal do baseline e exact match de células do candidato; um relatório
  pequeno registra ambiente, resultado e limitações;
- nenhum endpoint, dado persistido ou avaliação passa a depender do candidato nesta fatia.

Critérios da F4b:

- F4b-AC1 / REQ-006: a fixture tabular e sua referência esperada são determinísticas e versionadas
  como código de teste, sem artefato binário ou dado real no repositório.
- F4b-AC2 / REQ-006, REQ-013: o teste offline comprova localizadores de página/linha/coluna e não
  confunde célula vazia, zero e travessão.
- F4b-AC3 / REQ-013: o relatório não declara vencedor universal e a dependência candidata não entra
  no runtime; promoção exige amostra autorizada maior e critérios definidos antes da medição.

Resultado: a fixture obteve cobertura literal de 7/7 no baseline e exact match de 8/8 células no
candidato. A evidência, o ambiente e as limitações estão no
[relatório do baseline tabular](../quality/pdf-table-extraction-baseline.md).

#### Fatia F4c — baseline nativo de CSV/JSON

Status: `validado offline`.

Esta fatia define e mede o primeiro contrato de dados estruturados sem alterar ainda a API,
persistência ou avaliação orientadas a PDF:

- CSV usa cabeçalho obrigatório, nomes únicos e registros localizados por linha/coluna/campo;
- valores CSV permanecem strings literais, sem inferência silenciosa de número, booleano ou data;
- JSON aceita objeto ou lista não vazia de objetos com valores escalares, registra índice/campo e
  preserva os tipos `string`, `integer`, `number`, `boolean` e `null`;
- campo ausente, `null`, string vazia, zero, `false` e travessão são estados diferentes no contrato;
- encoding inválido, cabeçalho inválido, chave duplicada, linha excedente e valor JSON aninhado são
  falhas explícitas;
- o extrator permanece em `app/experiments/` e não é importado pelo entrypoint ou worker.

Critérios da F4c:

- F4c-AC1 / REQ-006: fixtures CSV/JSON em código têm referências determinísticas, sem dados reais
  ou artefatos binários.
- F4c-AC2 / REQ-004, REQ-006: testes offline comprovam localizadores e distinção exata entre
  ausência, nulo, vazio, zero, booleano e travessão, sem coerção implícita.
- F4c-AC3 / REQ-005, REQ-013: erros de contrato são explícitos e nenhum endpoint, tabela ou run
  passa a aceitar os novos formatos antes da generalização versionada de `DocumentUnit`.

Persistência, upload e interface para CSV/JSON ficam para uma fatia posterior porque o schema atual
exige página física em todas as unidades. Inventar página 1 violaria a proveniência; a integração
deverá introduzir localizador discriminado e migração compatível antes de admitir esses formatos.
Docling e OCR local também permanecem separados deste baseline nativo.

Resultado: as fixtures obtiveram exact match de 8/8 campos CSV e 8/8 campos JSON, além de rejeitar
os cinco casos inválidos definidos. A evidência e as limitações estão no
[relatório do baseline CSV/JSON](../quality/native-structured-extraction-baseline.md).

1. Usar pypdf/pdfplumber como baseline de PDF digital; conservar página, seção, texto e tabela
   sempre que disponíveis. Preservar original e valores literais; síntese é artefato derivado.
2. Separar metadados factuais de introdução/conclusão resumidas. Guardar `not_found`, `unreadable`
   e conflitos sem transformá-los em zero ou string vazia de sucesso.
3. Comparar Docling em uma amostra, sem substituir o baseline até medir resultado e custo local.
4. Habilitar OCR local seletivo em perfil extra, por exemplo OCRmyPDF/Tesseract, verificando as
   licenças/dependências da combinação instalada. Não tornar OCR gerenciado pago um requisito.
5. Adicionar CSV/JSON com leitura nativa e inspeção de tipos/linhas/campos. Não pedir ao LLM para
   reconstruir uma tabela que o parser já leu corretamente.
6. Mostrar fonte ao lado do campo, advertências de qualidade e limitações. Se não houver coordenada,
   citar página/unidade real; não inventar bounding box.

Gate: AC-006 em fixtures e relatório comparativo pequeno. Não precisamos implementar todas as
alternativas de extração para cumprir esta fase.

### F5 — laboratório de recuperação sem API paga obrigatória

Requisitos: REQ-009, REQ-012, REQ-013.

1. **Concluído no EV-01:** criar busca lexical simples como baseline sobre as unidades; mostrar
   resultado, origem e modo.
2. Habilitar pgvector no PostgreSQL local por migração incremental. Armazenar embeddings em tabela
   derivada vinculada às unidades, com modelo, dimensão, versão de chunk e parâmetros do índice;
   não recriar nem sobrescrever índices existentes silenciosamente.
3. Testar embedding local multilíngue, inicialmente `intfloat/multilingual-e5-small` como candidato
   compacto. Respeitar prefixos de query/passagem e tokenizer: sua ficha limita textos a 512
   tokens. Testar chunks de aproximadamente 200–400 tokens **desse tokenizer**, reservando espaço
   para prefixo/metadados; não reutilizar automaticamente os chunks de 700–1.000 de outros modelos.
   [Ficha do multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small/raw/main/README.md).
4. Validar estratégia de índice, memória e tempo na máquina. Se a extensão ou o perfil forem
   inviáveis, manter busca lexical disponível e registrar o experimento vetorial como pendente.
5. Conectar recuperação ao avaliador como modo opt-in. Mostrar o pacote de evidências e comparar
   com avaliação direta do mesmo documento, sem mudar a rubrica ao mesmo tempo.

Gate: AC-009 e AC-012. RAG deve provar evidência recuperada e cobertura; documentos de referência
não podem trazer rótulos de qualidade usados como gabarito oculto para o avaliador.

### F6 — judge e comparação de capacidades candidatas

Requisitos: REQ-010–013.

1. Criar judge que recebe parecer congelado, rubrica e evidências; testar citações inexistentes,
   números trocados, contradições e insuficiência. Não permitir correção silenciosa do parecer.
2. Habilitar segundo adaptador real somente se houver franquia e termos compatíveis, por exemplo
   Mistral Free mode. Mesmo modelo em duas chamadas serve ao teste funcional, mas não comprova
   independência da avaliação. Judge simulado serve só ao desenvolvimento de interface/contrato.
3. Implementar comparação A/B de runs e extrações; inicialmente 5–10 documentos para smoke test,
   depois 20 documentos autorizados para triagem, com repetições limitadas pela quota.
4. Medir validação de schema, evidências, erros por dimensão, latência e consumo; usar revisão
   humana de amostra para qualidade. Não classificar vencedor por opinião do próprio candidato.
5. Guardar configuração e exportar resultados. Evitar combinatória de todos os modelos × parsers
   × estratégias de busca: variar uma dimensão por vez.

Gate M2: AC-011 e AC-012, com separação clara entre testes funcionais e resultados científicos.
Hipóteses de serviço a demonstrar: extração, recuperação, avaliação e judge. Não há checkout,
assinatura ou promessa de API comercial nessa demonstração.

### F7 — estabilizar e preparar a versão documentada

Requisitos: REQ-001, REQ-013–015.

1. Executar instalação limpa, testes, build, walkthrough da interface, backup/restauração e uma
   demonstração offline completa. Registrar também o teste real ou sua pendência de acesso.
2. Reconciliar conceitos/pipelines e setup: o que está implementado, como executar, limites e quais
   recursos são experimentais. Não manter documentação dizendo que RAG está ativo quando estiver desligado.
3. Preencher Dockerfile de desenvolvimento/distribuição se necessário e composição local com
   perfis opcionais, fixando versões. Docker é conveniência, não pré-requisito de tudo no M1.
4. Preparar manual, capturas de tela sem dados pessoais, release notes, inventário de dependências,
   licenças/avisos de terceiros e evidências de testes. Escolha da licença do projeto fica com os titulares.
5. Ensaiar pacote técnico em diretório separado, excluindo credenciais, runtime, dados sensíveis e
   caches/modelos de terceiros. Identificar versão e hash do artefato exato, com instruções de guarda.
6. Apresentar o pacote ao mantenedor para aprovação de release e preparação institucional. Não
   criar tag/commit/push, publicar ou enviar pedido de registro sem autorização correspondente.

Gate M3: AC-015 e matriz de aceite preenchida com evidências; limitações residuais documentadas.
Uma versão pode ser preparada tecnicamente antes de todos os experimentos opcionais, desde que
escopo e recursos excluídos estejam explícitos e a aprovação correspondente seja registrada.

## Interface proposta: laboratório, não vitrine de SaaS

Navegação por quatro áreas, com funcionalidades liberadas por capability:

| Área | Experiência proposta | Entrega |
|---|---|---|
| Documentos | Lista local, upload, formato, páginas, qualidade e inspeção de texto/tabelas | F3–F4 |
| Avaliação | Configurar modo/modelo/rubrica, executar, ver seis dimensões e abrir evidências | F1, evoluindo em F3 |
| Busca | Pergunta/consulta, filtros, trechos e modo lexical/vetorial; sem chat obrigatório | F5 |
| Experimentos | Comparar extrações/pareceres, abrir judge, revisar métricas e exportar | F6 |

```text
┌─────────────────────────────────────────────────────────────────────┐
│ QA Method · Laboratório          Modo: demonstração / real   Saúde │
├─────────────┬───────────────────────────────────────────────────────┤
│ Documentos  │ Documento e revisão · configuração · Executar         │
│ Avaliação   ├─────────────────────────┬─────────────────────────────┤
│ Busca       │ Conteúdo / página       │ Campos / parecer / judge    │
│ Experimentos│ com origem verificável │ Evidências clicáveis        │
│             ├─────────────────────────┴─────────────────────────────┤
│             │ Etapa · modelo · duração · consumo · Exportar         │
└─────────────┴───────────────────────────────────────────────────────┘
```

Direção visual: preservar a identidade vermelha como acento, com superfícies neutras, tipografia
legível, espaçamento consistente e contraste adequado. Não depender de cor para comunicar status.
Cards de dimensão mostram nota/insuficiência, justificativa e fontes; evitar gráficos que sugiram
precisão científica não validada. Em telas estreitas, os painéis se empilham.

Estados obrigatórios: vazio com exemplo, recurso indisponível, upload inválido, extração parcial,
em execução, quota esgotada, falha e concluído. Botões têm labels, foco visível e feedback; recursos
futuros aparecem como “Planejado” sem link falso. Não transformar a interface em editor de chaves.

## Plano de validação

| Critério | Evidência planejada | Resultado nesta entrega |
|---|---|---|
| AC-001 | Instalação limpa, health e walkthrough demo | Validado na fatia F1: locks, instalação, health, SPA e fluxo demo verificados, inclusive no navegador |
| AC-002 | Contrato/UI/exportação de run simulado | Validado automaticamente: resultado, histórico e JSON exportado preservam a marcação simulada; inspeção visual F3c permanece no AC-008 |
| AC-003 | Smoke test real opt-in + teste de quota/chave ausente | Validado: smoke real passou com modelo/consumo registrados; chave ausente, quota e modelo indisponível têm cobertura de falha explícita |
| AC-004 | Testes parametrizados de erros e stream interrompido | Validado no contrato provisório: erros de entrada/provedor e JSON estruturado inválido não publicam sucesso; a futura API de runs será revalidada na F3 |
| AC-005 | Unidade de domínio/caso de uso sem rede | Validado na F2: domínio, demo e integração Gemini com cliente falso são exercitados sem rede |
| AC-006 | Fixtures digital, scan e tabular com localizadores | Parcial: F4a classifica páginas PDF, F4b valida tabelas PDF e F4c valida CSV/JSON nativos; OCR executável e integração persistente dos formatos permanecem pendentes |
| AC-007 | Integração de persistência, idempotência e reinício | Validado: persistência, idempotência, reload por URL, reexecução explícita e parada/reinício real do worker passaram na automação |
| AC-008 | Testes de componentes e walkthrough visual/teclado | Parcial: 15 testes frontend cobrem avaliação, busca e insights; EV-01–EV-03 passaram em desktop e 390 × 844 px, mas comparação/impressão e avisos de extração ainda requerem walkthrough ampliado |
| AC-009 | Consultas anotadas lexical/vetorial e índice indisponível | Validado: consulta lexical isolada e smoke vetorial anotado passaram; capacidade opt-in indisponível não bloqueia o modo lexical |
| AC-010 | Schemas, rubrica e referência humana em amostra separada | Parcial: schema das seis dimensões, insuficiência, notas e evidências está validado; qualidade semântica ainda requer corpus e revisão humana |
| AC-011 | Judge contra pareceres congelados e erros controlados | Pendente |
| AC-012 | Comparação, versionamento e exportação de dois runs | Validado automaticamente: dois runs do mesmo documento expõem configuração, duração, consumo e dimensões; JSON/Markdown/impressão estão disponíveis |
| AC-013 | Suíte offline e isolamento dos testes reais | Validado no EV-03: 97 testes backend, 15 frontend, builds, smoke HTTP/RAG e backup/restore passaram em contêineres sem credenciais |
| AC-014 | Bind, CORS, validação de upload, segredos e consentimento | Parcial: loopback, CORS, limites, allowlist e consentimento verificados; revisão amplia nas próximas fases |
| AC-015 | Manual, restore de backup e checklist técnico de versão | Pendente |

### Evidências executadas em 2026-09-10

- `uv sync --locked --group dev`, `uv pip check`, `ruff check app tests` e
  `pytest -m "not live"`: passaram em Python 3.12.14; 19 testes passaram. O TestClient emitiu dois
  avisos de depreciação de dependências, sem falha.
- `npm ci`, `npm run typecheck`, `npm run lint`, `npm run test:run` e `npm run build`: passaram em
  Node 24.20.0; 1 teste de componente passou e o build Vite foi produzido.
- `npm audit`: zero vulnerabilidades após atualizações controladas para React Router 7.18.3 e
  PostCSS 8.5.28.
- Smoke HTTP com servidores em loopback: health, capabilities, upload demo, página Vite e preflight
  CORS responderam 200; o resultado registrou `simulated: true`.
- Walkthrough com Chrome for Testing e `agent-browser`: home e avaliação carregaram sem overlay ou
  erros de página; upload e execução demo exibiram as seis dimensões em desktop e viewport de
  390 px. A exportação baixada registrou `simulated: true` e “Simulado — sem inferência LLM”. As
  bibliotecas do navegador foram extraídas somente em `/tmp`, sem instalação no host.
- `pytest -m "not live"` na raiz: 19 testes passaram. Em 2026-09-10, `ruff check .` ainda incluía
  notebooks históricos e registrou 62 achados; a decisão posterior retirou-os do escopo ativo.
- Busca por padrões comuns de segredo e `git diff --check`: sem achados nos arquivos da fatia e sem
  erros de whitespace. Nenhuma inferência externa foi executada.

### Evidências containerizadas executadas em 2026-09-13

O mantenedor informou aprovação das etapas offline do runbook, incluindo upload, exportação,
desktop/mobile e teclado da F1. Depois, em 2026-09-13, executou também a seção 11 com a fixture
sintética e o modelo gratuito `gemini-3.5-flash-lite`; AC-003 foi validado sem misturar o teste
real à suíte offline.

- `./scripts/test-containers.sh`: construiu os targets de runtime e teste; Ruff passou; 19 testes
  backend e 1 teste frontend passaram; typecheck, ESLint e build Vite passaram.
- O mesmo comando iniciou API e interface com healthchecks e concluiu o smoke test de `/health`,
  `/capabilities` e entrega da SPA. Os serviços foram removidos ao final.
- Os contêineres das suítes rodaram com rede desabilitada e credenciais explicitamente vazias. A
  automação foi registrada em `.github/workflows/container-quality.yml`; sua execução remota ainda
  depende do próximo push/PR.
- Após a integração F2b, `./scripts/test-containers.sh` foi repetido: Ruff, 39 testes backend,
  typecheck, ESLint, 1 teste frontend, build Vite e smoke da stack passaram. Dois avisos conhecidos
  de depreciação do TestClient permanecem sem reprovar a suíte. Não houve chamada externa.
- Após PostgreSQL, failover e diagnóstico do provedor, a suíte foi repetida com 46 testes backend;
  Ruff, typecheck, ESLint, Vitest, builds e smoke local passaram. Separadamente, o mantenedor
  executou `./scripts/test-gemini-live.sh`: uso real pela credencial principal, 272 tokens de
  entrada, 880 de saída e seis dimensões.
- Após a F3b, em 2026-09-14, a suíte passou com 55 testes backend e o smoke passou a admitir um
  documento, criar a solicitação idempotente, aguardar o worker e validar o resultado persistido.
  O teste continuou offline, encerrou a stack e removeu o volume isolado ao final.
- Após a F3c, no mesmo dia, a suíte passou com 56 testes backend e 3 frontend. O frontend passou a
  usar documentos/runs, reabrir `?run=<id>`, listar histórico e reexecutar interrupções com novo ID;
  o smoke confirmou que o run criado aparece na listagem. O walkthrough ampliado ficou pendente
  porque não havia executável `agent-browser`, Chromium ou Chrome neste ambiente.
- Após a F3d, a suíte passou com 56 testes backend e 5 frontend. O smoke operacional restaurou um
  dump após remover os dados do volume isolado e comprovou a reconciliação de um run `running` pelo
  processo real do worker. Comparação e exportação Markdown passaram em testes; os controles e o
  layout de impressão passaram em typecheck/lint/build, mas a prévia visual segue pendente pela
  mesma indisponibilidade de navegador.
- Após a F4a, em 2026-09-14, a suíte passou com 58 testes backend e 5 frontend. Fixtures sintéticas
  comprovaram `extracted`, `ocr_candidate` e `no_text`; a migração e o smoke reabriram os sinais por
  `GET /api/v1/documents/{id}/pages`. A interface apresentou extração completa/parcial em teste de
  componente. O walkthrough visual continuou indisponível por ausência de navegador local.
- Após F4b/F4c, em 2026-09-15, a suíte passou com 66 testes backend e 5 frontend. Os experimentos
  offline reproduziram tabelas de PDF e estruturas CSV/JSON sem promover suporte ao runtime.
- Após o EV-01, no mesmo dia, a suíte passou com 75 testes backend e 9 frontend. O smoke admitiu um
  PDF, pesquisou a expressão anotada e validou página, unidade, trecho e modo lexical. A tela `/search`
  passou em 1440 × 900 px e 390 × 844 px, no fluxo integral por teclado, sem erros de console,
  rolagem horizontal ou violações WCAG A/AA detectadas pelo axe-core.
- Após o EV-02, a suíte passou com 82 testes backend e 11 frontend. O smoke opt-in com fixture
  sintética e embedding local recuperou a página anotada em top-1, registrou 44,907 s no primeiro
  uso em volume novo e 0,034 s na reutilização. O walkthrough comparou ambos os modos em desktop e
  390 × 844 px,
  sem erros de console ou violações WCAG A/AA detectadas.
- Após o EV-03, a suíte passou com 97 testes backend, 15 frontend, builds, smoke de avaliação e
  insight, backup/restore e reinício do worker. O walkthrough criou e reabriu um insight em desktop
  e 390 × 844 px, exibiu a evidência E1 e sua origem e terminou sem erros da aplicação ou violações
  detectadas pelo axe-core.

Os comandos equivalentes no host continuam disponíveis para diagnóstico específico:

```bash
# qa-services/ — ambiente do serviço ativado
python -m pip check
ruff check app tests
pytest -m "not live"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
# qa-application/
npm ci
npm run typecheck
npm run lint
npm run test:run
npm run build
npm run dev -- --host 127.0.0.1
```

Nas próximas fases, atualizar os targets quando uma dependência de runtime/teste mudar e usar
verificação visual sempre que iniciar uma nova interface. A suíte `live` exige habilitação
explícita, corpus autorizado e orçamento/quotas conferidos.
Não reportar cobertura, acurácia ou “passou” sem evidência de execução.

## Preparação para o registro de software

Esta é uma trilha documental e institucional, não uma funcionalidade de SaaS nem um parecer
jurídico. O guia do INPI orienta preparação do resumo hash e documentos do pedido; a SINOVA/UFSC
publica fluxo institucional específico. Conferir o procedimento vigente e a titularidade aplicável
com orientador/instituição antes de protocolar. Não presumir que ser autor de TCC resolve sozinho
a titularidade do software. [Guia INPI](https://www.gov.br/inpi/pt-br/servicos/programas-de-computador/guia-basico),
[fluxo SINOVA/UFSC](https://sinova.sites.ufsc.br/registro-de-programa-de-computador/).

Checklist de preparação, sem envio nesta etapa:

- [ ] Identificar autores, contribuições, vínculo institucional e possíveis titulares/parceiros.
- [ ] Definir nome/versão e descrição funcional do software efetivamente implementado.
- [ ] Separar código próprio, dependências, modelos, dados e contribuições de terceiros.
- [ ] Revisar licenças e autorizações; não atribuir ao projeto a autoria dos modelos utilizados.
- [ ] Preservar histórico de desenvolvimento e documentar contribuições/revisões, inclusive uso de IA.
- [ ] Reunir arquitetura, manual, instruções de build, testes e demonstração autorizada.
- [ ] Produzir cópia técnica estável e manifesto do conteúdo; gerar hash do artefato exato segundo
  o procedimento aplicável, preservando-o. Hash do commit não substitui automaticamente esse artefato.
- [ ] Definir guarda, backup e responsáveis pela documentação técnica e credenciais de assinatura.
- [ ] Confirmar com a instituição documentos, assinaturas, taxas e autorizações antes do pedido.

Testes locais podem priorizar gratuidade; o procedimento formal de registro pode envolver taxas
e certificado digital, portanto não está incluído na promessa de “sem contratação para testar”.
O [guia do INPI](https://www.gov.br/inpi/pt-br/servicos/programas-de-computador/guia-basico) é a referência
para conferir essas exigências na data do protocolo. Preparar uma versão demonstrável é uma
decisão de organização deste projeto, não declaração de requisito legal de interface ou benchmark.

## Questões abertas e gates

| Questão | Responsável por confirmar | Onde bloqueia | Caminho independente |
|---|---|---|---|
| RAM/CPU/GPU e espaço disponíveis | Mantenedor | Escolha de IA/OCR local pesada | Demo, parsing digital e busca lexical |
| Continuidade de quota gratuita | Mantenedor | Benchmarks reais adicionais | Testes offline, demo e smoke real já registrado |
| Corpus autorizado e anotadores | Mantenedor/orientador | Alegações de qualidade | Fixtures sintéticas e smoke tests |
| Versões resolvidas e compatibilidade | Implementador em F0/F1 | Build/instalação específicos | Não aprovar resolução sem executar testes |
| Schema/códigos finais de cada endpoint | Implementador + mantenedor antes da fase | Fase que altera o contrato | Manter funcionalidade anterior até contrato aprovado |
| Autoria, titularidade e licença | Autores/instituição | Distribuição e protocolo de registro | Desenvolvimento/testes locais autorizados |

Não é necessário resolver SaaS ou escolher o melhor modelo universal para começar F0/F1.
Antes de implementar fases com contrato novo, fechar os detalhes bloqueantes e atualizar a
especificação conforme o [processo do projeto](../processes/spec-driven-development.md).

## Desvios

F0 foi registrada e a fatia F1 foi implementada. O contrato provisório deixou de usar streaming de
texto para impedir sucesso truncado e passou a JSON completo; a API persistente de runs passou a
ser o caminho da interface na F3. A persistência PostgreSQL de documentos iniciou na F3a, os
runs/worker na F3b, a interface persistente na F3c, a comparação/recuperação operacional na F3d, a
extração experimental nas F4a–F4c e as buscas EV-01/EV-02 e os insights EV-03 na F5. A rota
provisória permanece apenas para compatibilidade; OCR, judge, estabilização final, teste real do
insight e walkthrough ampliado das telas anteriores ainda estão pendentes.
