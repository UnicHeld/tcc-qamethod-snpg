# Insights RAG rastreáveis

- **Status:** `em-implementacao`
- **Última atualização:** 2026-09-16
- **Especificação relacionada:** [insights RAG rastreáveis](../specs/rag-insights.md)
- **Decisões relacionadas:** [recuperação vetorial local](../decisions/local-vector-retrieval.md)

## Contexto

As buscas lexical e vetorial recuperam trechos verificáveis de uma revisão persistida, mas ainda
não produzem uma resposta baseada nesses trechos. A avaliação vigente lê o documento diretamente e
deve continuar separada para preservar o baseline e a rubrica.

O EV-03 adiciona uma pergunta única, um pacote congelado de evidências e uma resposta citável. O
fluxo usa os mesmos modos demo/real e as mesmas restrições de consentimento já aplicadas ao
avaliador. Não é chat e não altera o contrato de `EvaluationReport`.

## Objetivos e não objetivos

### Objetivos

- Persistir uma solicitação assíncrona de insight para um documento e uma pergunta.
- Recuperar e congelar os trechos usados antes da geração.
- Validar todas as citações contra o pacote congelado e a revisão do documento.
- Permitir reabrir e exportar pergunta, configuração, resposta e evidências.
- Preservar avaliação direta e busca lexical quando RAG ou pgvector estiverem indisponíveis.

### Não objetivos

- Chat multi-turno, memória conversacional ou busca entre documentos.
- Alterar notas, dimensões ou prompt do avaliador direto.
- Comprovar correção semântica, substituir revisão humana ou executar judge.
- Persistir o PDF original ou publicar o serviço sem autenticação.

## Estado atual

`POST /api/v1/search` devolve hits lexicais ou vetoriais com unidade, página, trecho e score. O
worker atual processa somente `evaluation_runs`. PostgreSQL é a fonte de documentos, unidades,
runs e resultados; embeddings são derivados reconstruíveis.

## Desenho proposto

```text
POST /api/v1/insights -> insight_run queued
  -> worker recupera hits lexical/vetorial
  -> congela EvidencePackage (revisão + perfil + E1..En + origem)
  -> adaptador demo/Gemini recebe somente pergunta + pacote
  -> valida InsightReport.citation_ids contra E1..En
  -> persiste pacote + resposta + Markdown de forma atômica
  -> GET /api/v1/insights/{id}/result
```

Uma fila própria evita misturar o schema da avaliação com o de insight. O mesmo processo de worker
atende as duas filas, usando repositórios e transações independentes. Avaliações e insights
continuam identificados por recursos distintos.

O pacote atribui IDs locais `E1`, `E2`, ... na ordem determinística da recuperação. Cada item
preserva `unit_id`, página, trecho exato enviado ao gerador e score. Citações do modelo só podem usar
esses IDs. Ausência de hits encerra o run como falha antes de qualquer geração.

## Interfaces e dados

- `POST /api/v1/insights`: documento, pergunta, recuperação lexical/vetorial, limite, modo
  demo/real e confirmação externa. Aceita `Idempotency-Key`.
- `GET /api/v1/insights`: histórico recente, opcionalmente filtrado por documento.
- `GET /api/v1/insights/{id}`: estado e configuração, sem publicar resultado parcial.
- `GET /api/v1/insights/{id}/result`: pacote, resposta validada e Markdown após sucesso.

A migração `0006_rag_insight_runs.sql` cria uma tabela aditiva. Pacote e relatório são JSONB
canônicos; Markdown é derivado. O resultado registra modelo de embedding/dimensão/chunk quando o
modo vetorial for usado e mantém esses campos nulos no modo lexical.

## Segurança, privacidade e abuso

O documento e a pergunta são dados não confiáveis. O prompt proíbe seguir instruções contidas nas
evidências, executar ferramentas, acessar links ou completar fatos fora do pacote. Em modo real,
somente pergunta e trechos recuperados são enviados ao provedor após confirmação explícita; o PDF
completo não é enviado por este fluxo. Segredos não entram em respostas ou exportações.

Pergunta, limite e quantidade de evidências possuem limites. Resposta HTML não é aceita. IDs de
citação inexistentes invalidam toda a geração.

## Confiabilidade e operação

Runs abandonados em `running` tornam-se `interrupted` no início do worker e não são repetidos
automaticamente. Timeout, quota, modelo indisponível, busca vetorial indisponível e ausência de
evidência produzem falhas explícitas. Nenhuma resposta parcial é publicada.

O primeiro uso vetorial pode baixar e materializar o modelo local; continua opt-in. O perfil
lexical não depende do modelo. Backup/restore do PostgreSQL passa a incluir runs e pacotes de
insight, mas não o PDF original.

## Alternativas consideradas

| Alternativa | Benefícios | Custos e riscos | Resultado |
|---|---|---|---|
| Estender `evaluation_runs` | Menos tabelas/endpoints | Mistura dois resultados e fragiliza compatibilidade | Descartada |
| Geração síncrona no endpoint | Implementação menor | Request longo, pouca recuperação após falha | Descartada |
| Fila própria de insights | Contrato e ciclo de vida explícitos | Novo repositório e migração | Escolhida |
| Chat multi-turno | Experiência familiar | Memória, custo e escopo não necessários | Descartada |

## Rollout e rollback

Os endpoints e a tabela são aditivos. A interface só oferece o modo vetorial quando a capability o
habilita. Em rollback de aplicação, a tabela pode permanecer sem afetar avaliações ou buscas; não
há migração destrutiva.

## Validação do desenho

- Testes de domínio rejeitam citações fora do pacote e revisão incompatível.
- Testes de serviço cobrem pacote determinístico, ausência de hits e demo offline.
- Testes HTTP cobrem idempotência, consentimento, estados e publicação após sucesso.
- Teste PostgreSQL cobre migração, fila e persistência atômica.
- Testes de componente cobrem criação, polling, evidências e exportação.

## Questões abertas

- Nenhuma decisão bloqueante para o EV-03. Qualidade semântica permanece um experimento posterior
  dependente de corpus autorizado e revisão humana.
