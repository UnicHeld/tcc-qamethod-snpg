# Desenho proposto para recuperação do protótipo QA Method

- Status: `parcialmente implementado` — F1–F5 descrevem o runtime até o EV-03; F6/F7 permanecem
  como alvo.
- Última atualização: 2026-09-15.
- Especificação relacionada: [roteiro de recuperação](../specs/prototype-recovery.md).
- Decisões relacionadas: [execução e testes com Compose](../decisions/containerized-development-and-testing.md), além do
  [arquivamento dos notebooks da POC](../decisions/archive-poc-notebooks.md), da
  [persistência PostgreSQL](../decisions/postgresql-local-persistence.md) e do
  [failover de credenciais Gemini](../decisions/gemini-credential-failover.md).

## Contexto

Recuperar a execução local, organizar os componentes existentes e transformar a interface em um
laboratório demonstrável de inteligência documental. O usuário priorizou recursos gratuitos e
adiou SaaS; portanto, não se assume multitenancy, cobrança, usuários externos ou nuvem gerenciada.

Premissas de desenho: um operador confiável, instalação local, corpus pequeno e autorizado, API
sem exposição pública e uma tarefa pesada por vez. Hardware para OCR/LLM local e quotas de conta
ainda não foram confirmados; esses recursos devem permanecer opcionais.

## Objetivos e não objetivos

### Objetivos

- Inicializar API/interface sem credenciais, separando demonstração de inferência real.
- Preservar o método de seis dimensões e recuperar avaliação real com SDK/modelo suportados.
- Desacoplar leitura documental, recuperação, avaliação e judge em módulos testáveis.
- Inspecionar evidências, resultados e experimentos por uma interface consistente.
- Guardar execuções reproduzíveis e preparar documentação técnica da versão do software.

### Não objetivos

SaaS, autenticação pública, tenants, faturamento, deploy em nuvem, alta disponibilidade, grafos,
chat aberto, agentes autônomos, comparação de todos os LLMs ou suporte universal a formatos.
Não alterar rubrica ou agregar as seis notas em uma nota final sem decisão acadêmica específica.

## Estado inicial confirmado em F0

As páginas de [conceitos](fundamental-concepts.md), [avaliação](evaluation-pipeline.md) e
[RAG](rag-pipeline.md) precisam ser reconciliadas conforme a implementação evoluir. A inspeção
encontrou um fluxo web direto `PDF → texto → Gemini → stream`; recuperação não é chamada pelo
avaliador. Essa diferença entre intenção documental e execução orienta a recuperação incremental.

| Local | Evidência confirmada | Implicação |
|---|---|---|
| Manifesto e Dockerfile do backend | Vazios no baseline | Era necessário definir instalação isolada e reproduzível |
| [Router de avaliação](../../qa-services/app/routers/evaluation.py) | Inicializa clientes no import; exceção genérica captura inclusive HTTPException | Credencial acoplada ao carregamento; erro de entrada pode virar 500 |
| [Serviço avaliador](../../qa-services/app/services/evaluation_service.py) | SDK legado, modelo fixo e exceção capturada sem propagar resultado de falha | Stream pode encerrar sem informar erro claramente |
| [Configuração](../../qa-services/app/core/config.py) | Carregamento de configuração não centralizado no entrypoint | Precisará de configuração única e validação por capacidade |
| [Parser](../../qa-services/app/services/parser_service.py) | Texto concatenado, sem OCR ou proveniência de trecho | Melhorar representação antes de avaliar documentos difíceis |
| [Frontend](../../qa-application/package.json) | CRA 5, React 18, TS 4.9 e Tailwind 3 | Atualizar ferramenta de build em passo controlado |
| [Página de avaliação](../../qa-application/src/pages/Evaluation.tsx) | Upload inicia inferência; URL fixa e resultado só no estado da tela | Separar seleção, configuração, execução e histórico |
| [Cartões](../../qa-application/src/components/ServiceCard.tsx) | Funcionalidade sem rota vira link `#` | Distinguir recurso disponível, experimental e planejado |

No shell inspecionado, `python3` é 3.14.7, Node é 24.20.0 e npm é 11.19.0. Isso não comprova
compatibilidade das dependências nem execução do projeto. O setup antigo recomenda Python 3.12;
o roteiro propõe fixar explicitamente o interpretador do serviço em vez de usar o padrão da máquina.

Desde a entrega F1, os manifests, testes e fluxo offline foram implementados. A execução
containerizada descrita abaixo foi incorporada em 2026-09-13; a tabela preserva a fotografia que
motivou a recuperação, não o estado atual dos arquivos.

## Desenho proposto

### Componentes e fluxo

```text
React/TypeScript + Vite (um laboratório, várias telas)
                           │ HTTP local / polling de tarefas
                           ▼
FastAPI: configuração, validação HTTP e casos de uso
  ├─ documentos: admissão, parsing, extração de campos e evidências
  ├─ recuperação: busca lexical / pgvector + embeddings locais
  ├─ avaliação: rubrica, pacote de evidências e resultado tipado
  ├─ judge: crítica do parecer com referências, sem sobrescrever notas
  └─ experimentos: configurações, comparação e exportação
                           │
                fila persistida + worker local único
                  ↙                         ↘
        adaptadores de parsing/LLM      PostgreSQL + pgvector + arquivos locais
        mock / free API / local         vetores opcionais e reconstruíveis
```

Módulos compartilham um processo de API e uma base de código. O worker é outro processo da mesma
aplicação, introduzido somente na fase de histórico/tarefas. Não criar serviços de rede internos
para cada responsabilidade. O caminho mínimo de boot não depende do worker, de pgvector ou de LLM.

### Organização alvo, incremental

```text
qa-services/
  app/
    main.py                 # composição e ciclo de vida
    core/                   # configuração, erros, logging
    routers/                # HTTP fino
    domain/                 # rubrica e contratos, sem SDKs de fornecedores
    services/               # casos de uso por capacidade
    adapters/               # parsing, modelos, índices, arquivos e PostgreSQL
    worker.py               # executor local de tarefas
  tests/                    # unidade, contrato e integração
  pyproject.toml            # dependências diretas, extras e configuração de ferramentas
  requirements*.txt         # resoluções fixadas para instalação reproduzível
qa-application/
  src/
    components/             # componentes compartilhados
    features/               # documentos, avaliação, busca, judge, experimentos
    lib/                    # cliente HTTP e tipos de transporte
    pages/                  # composição das telas e rotas
```

São diretórios propostos, não arquivos já existentes. Reaproveitar `services/` e `routers/` antes
de mover módulos; não fazer reorganização em massa junto da troca de SDK. `notebooks/` e as
dependências da raiz ficam preservados somente como arquivo histórico da POC e não participam da
evolução. Preferir dependências já presentes no serviço quando resolverem a necessidade, e extras
opcionais para OCR, embeddings e novos formatos.

### Stack e perfis

Python 3.12 é o baseline proposto para reduzir a distância da documentação e testar disponibilidade
de dependências de parsing; validar e fixar patch/resolução na primeira fase. Node 24 LTS atende à
direção de atualização; não trocar o runtime global da máquina. A fonte Node lista 24 como LTS e
18/20 como EOL na data consultada. [Releases Node](https://nodejs.org/en/about/previous-releases).

Migrar CRA para Vite preservando componentes e inicialmente sem elevar simultaneamente todos os
majors de React, Router e Tailwind. Depois dos testes básicos, atualizar dependências em grupos
compatíveis, documentando vulnerabilidades/pendências. Não manter versão vulnerável só para
preservar build, nem executar correções forçadas sem inspecionar os impactos.

O perfil `demo` usa fixtures determinísticas e parsing real quando disponível. `free-api` usa um
adaptador real configurado e habilitado explicitamente. `local-ai` exige modelo instalado e teste
de recursos.

O Compose possui uma topologia mínima de três processos: FastAPI, SPA/Nginx e PostgreSQL. Nginx encaminha
`/api` para o backend pela rede interna, enquanto somente as portas de loopback 5173 e 8000 são
publicadas no host; o banco permanece apenas na rede do Compose. Targets de desenvolvimento adicionam hot reload; targets de teste instalam as
ferramentas de qualidade e executam sem rede. A extensão pgvector e OCR só entram quando houver
capacidade implementada e teste correspondente; o worker já integra a topologia padrão. A decisão
e os trade-offs estão em
[execução e testes com Compose](../decisions/containerized-development-and-testing.md).

## Interfaces e dados

### Contratos internos e resposta F2

A fatia F2a implementa os contratos internos. Uma revisão
extraída usa o SHA-256 completo dos bytes como identidade e uma unidade por página com texto,
identificada por `<sha256>:page:<n>`. Páginas vazias não geram unidades, mas continuam na contagem
e na numeração física. Não há persistência nesta fatia.

O parecer tipado valida seis dimensões únicas, notas finitas de 0 a 10 ou insuficiência com nota
nula, justificativas não vazias e evidências pertencentes à revisão. A validação de referências
ocorre contra o documento, fora de clientes LLM. Markdown é derivado apenas após essa validação.
A F2b conecta o mesmo `EvaluationDraft` aos adaptadores demo/Gemini e adiciona à resposta pública
`document.units` (somente ID/página) e `report`, preservando os campos F1. O cliente Gemini solicita
JSON pelo schema e qualquer resultado inválido encerra a chamada como falha, sem sucesso parcial.

| Objeto | Campos/responsabilidade mínimos propostos |
|---|---|
| `DocumentRevision` | ID, hash de conteúdo, formato, tamanho, origem autorizada, revisão e status |
| `DocumentUnit` | ID, revisão, tipo, texto/tabela, localizador de página/célula e versão do parser |
| `DocumentPage` | Página física, estado de extração conservador, caracteres e presença de imagem raster |
| `EvidenceBundle` | Unidades selecionadas, consulta, modo de recuperação, cobertura e lacunas |
| `EvaluationReport` | Seis dimensões, nota ou insuficiência explícita, justificativa, evidências e versão da rubrica |
| `JudgeReport` | Avaliação de fundamentação/consistência do parecer, achados e evidências; sem alterar o relatório fonte |
| `Run` | Tipo de tarefa, modo real/simulado, configuração, status, uso, duração, erros, IDs de entrada/saída |
| `Experiment` | Conjunto de runs comparáveis, corpus/versionamento, parâmetros e observações humanas |

Nota 0 não significa “sem evidência”. Insuficiência deve ter status próprio e nota ausente conforme
contrato a validar na fase da rubrica. `EvaluationReport` e `JudgeReport` precisam ser validados
antes de publicação; Markdown é uma visualização, não o banco de dados do resultado.

Na F4a, `DocumentPage` não é um parecer semântico. `ocr_candidate` registra somente “sem texto
extraído e com imagem raster detectada”; `no_text` registra “sem texto nem imagem raster detectada”.
Nenhum desses estados prova que a página esteja vazia ou ilegível, e nenhum dispara OCR
automaticamente. As unidades textuais continuam sendo a única evidência consumida pelo avaliador.

Na F4b, o adaptador pdfplumber permanece em `app/experiments/` e só existe na imagem de testes.
Seu contrato de tabela usa página física e células por linha/coluna, preservando texto literal ou
ausência. O entrypoint, o worker, a persistência e os manifests de runtime não o importam. Assim o
experimento compara representação sem alterar simultaneamente o fluxo avaliado em produção.

Na F4c, CSV e JSON recebem localizadores próprios de registro, linha, coluna e campo. O baseline
experimental preserva valor, presença e tipo sem tentar encaixar dados estruturados no número de
página obrigatório do contrato vigente. A futura integração persistente deverá transformar
`DocumentUnit` em uma união discriminada de localizadores por formato e migrar dados PDF existentes
antes de ampliar o MIME aceito pela API. Até lá, CSV/JSON não entram em endpoints nem em runs.

### API alvo

Os endpoints de documentos e runs abaixo estão implementados nas F3a/F3b; busca e experimentos
continuam como alvo das fases seguintes.

| Endpoint proposto | Função |
|---|---|
| `GET /health` | Liveness sem chamar modelo externo |
| `GET /capabilities` | Módulos/perfis habilitados e motivos de indisponibilidade, sem expor chaves |
| `POST /api/v1/documents` | Admitir arquivo e criar ID/revisão |
| `GET /api/v1/documents/{id}` | Estado e metadados da revisão |
| `GET /api/v1/documents/{id}/units` | Inspecionar unidades extraídas |
| `GET /api/v1/documents/{id}/pages` | Inspecionar cobertura e sinais conservadores da extração por página |
| `POST /api/v1/runs` | Solicitar extração, avaliação ou judge com parâmetros validados |
| `GET /api/v1/runs` | Listar runs recentes, opcionalmente filtrados por documento |
| `GET /api/v1/runs/{id}` | Estado, métricas e referência ao resultado |
| `GET /api/v1/runs/{id}/result` | Resultado validado ou motivo de indisponibilidade |
| `POST /api/v1/search` | Recuperar evidências, sem geração de resposta obrigatória |
| `GET /api/v1/experiments/{id}` | Consultar comparação persistida |

Criar/listar experimentos e exportar resultados entram no contrato detalhado da fase correspondente.
Não publicar endpoints vazios só para completar esta tabela. Polling é suficiente inicialmente;
streaming de progresso será opcional, sem depender dele para preservar o resultado.

No EV-01, `POST /api/v1/search` implementa recuperação lexical sobre `document_units` de um
documento explícito. PostgreSQL calcula correspondência/ranking textual; o serviço limita e recorta
trechos em texto simples. A consulta não é persistida e não atravessa adaptador de LLM. Esse contrato
é ampliado de forma aditiva no EV-02 com `retrieval_mode: "vector"`, sem retirar o modo lexical.
O modo vetorial usa um adaptador FastEmbed carregado sob demanda, materializa chunks versionados e
persiste somente derivados reconstruíveis. Modelo, dimensão e versão do chunk acompanham a resposta.

Manter `/evaluation/upload` temporariamente na retomada para compatibilidade, corrigindo tratamento
de erro. A interface migra para runs na fase persistente; documentar retirada da rota antiga e não
montar o router documental antigo sem validar destinos e formatos.

### Persistência e migração

PostgreSQL é a fonte de metadados, estados, unidades e referências; arquivos locais gerenciados
guardarão originais e artefatos. Na F5, pgvector armazena embeddings derivados e reconstruíveis,
sempre vinculados às unidades que permanecem como fonte do conteúdo. A API e o worker compartilham
o contrato de repositório, mas não conexões ou transações abertas.

Migrações SQL são incrementais, registradas no próprio banco e executadas antes da API. A F3a cria
documentos e unidades com IDs estáveis e idempotência pelo hash do conteúdo. Escritas futuras de
arquivo devem ser atômicas; confirmar metadados após materialização e reconciliar artefatos órfãos.
Na F4a, `document_pages` registra uma linha por página física e referencia o documento com
`ON DELETE CASCADE`; a migração classifica unidades legadas com texto como `extracted` e demais
páginas como `no_text`, pois os bytes originais ainda não são armazenados para reanálise. Um novo
upload idêntico atualiza esses sinais a partir dos mesmos bytes. Backup/restauração usam ferramentas
PostgreSQL e serão ensaiados antes de dados úteis. Não importar
JSON/vetores antigos automaticamente. A migração vetorial deve criar a extensão e novas estruturas
de forma incremental, sem recriar tabelas ou índices existentes silenciosamente.

A migração pgvector é opcional: quando a extensão não estiver disponível no servidor, ela não é
marcada como aplicada e as demais migrações e a busca lexical continuam. No perfil vetorial, a
imagem PostgreSQL contém a extensão e a migração cria o índice derivado. A decisão de runtime,
modelo e chunk está em [recuperação vetorial local](../decisions/local-vector-retrieval.md).

## Segurança, privacidade e abuso

API e ferramentas locais vinculadas a `127.0.0.1`, CORS por origem e headers explícitos e sem exposição pública.
CORS não substitui autenticação; qualquer uso remoto demanda revisão de segurança fora deste plano.
Segredos só no backend, nunca em configuração pública do bundle ou exportação. Capabilities deve
mostrar disponibilidade, não valores de credenciais.

Uploads têm limites de bytes/páginas, validação de formato e IDs do servidor. Parsing com limite de
tempo/memória; macros e instruções embutidas não são executadas. Não renderizar HTML arbitrário de
LLM. Antes de inferência remota, mostrar provedor, modo, dado a enviar e confirmação explícita.
Usar documentos sintéticos/públicos autorizados e observar termos de uso de dados dos free tiers.

## Confiabilidade e operação

Proposta inicial: um worker e um run pesado ativo. Estados persistidos `queued`, `running`,
`succeeded`, `partial`, `failed`, `interrupted`. Após reinício do worker, execuções abandonadas são
marcadas `interrupted`; o operador decide reexecutar. Não prometer retomada automática exatamente
do ponto da chamada LLM nem execução exatamente uma vez.

IDs de requisição/idempotência impedem submissão duplicada por recarregar a tela. Reexecução cria
novo run vinculado ao anterior. Timeouts e retries são limitados e não ocultam possível consumo da
tentativa anterior. Quando duas credenciais gratuitas de projetos distintos estiverem configuradas,
somente um `429` da principal autoriza uma tentativa na reserva. Não há fallback em outros erros,
troca de modelo, demo ou plano pago; o resultado registra apenas o slot de credencial utilizado.

Logs estruturados por run/estágio, sem texto integral ou segredos por padrão. Distinguir consumo
real, estimativa, valor desconhecido e desembolso zero por franquia. Persistir versões do modelo,
prompt, parser, embedding, rubrica e configurações para comparação.

## Alternativas consideradas

Este desenho não presume adoção anterior de SaaS ou de multiagentes.

## Rollout e rollback

Aplicar o [roteiro por fases](../specs/prototype-recovery.md), com uma entrega executável por etapa.
Versionar contratos e configurações, preservar dados antigos e usar perfis/flags para recursos
experimentais. Reverter o adaptador ou desabilitar o experimento sem apagar resultados. Mudanças
de banco/índice exigem backup e estratégia de reversão validada antes da migração de dados úteis.

## Validação do desenho

- Boot offline sem credenciais; demonstração não se apresenta como avaliação real.
- Extração rastreável, schemas e erros exercitados por fixtures sem provedores externos.
- Reinício da interface não perde resultado; reinício do worker não deixa run indefinidamente ativo.
- Comparação com mesmo documento/rubrica evidencia diferenças sem proclamar vencedor automático.
- Recursos opcionais indisponíveis não impedem o restante do laboratório.

## Questões abertas

Hardware e quotas condicionam apenas extras de IA/OCR e testes reais. Corpus e anotadores
condicionam validação de qualidade. Titularidade e licença condicionam distribuição/registro,
não o desenvolvimento local do protótipo. Essas dependências e seus gates estão no roteiro;
este documento não declara a implementação pronta ou aprovada em todos os detalhes.
