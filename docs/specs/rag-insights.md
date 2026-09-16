# Insights RAG rastreáveis

- **Status:** `em-implementacao`
- **Responsável:** a definir com o mantenedor
- **Última atualização:** 2026-09-16
- **System design:** [insights RAG rastreáveis](../architecture/rag-insights-design.md)
- **Decisões relacionadas:** [recuperação vetorial local](../decisions/local-vector-retrieval.md)

## Contexto e problema

EV-01 e EV-02 permitem localizar evidências, porém o usuário ainda precisa interpretar os hits sem
uma síntese rastreável. Gerar diretamente sobre o documento esconderia quais trechos sustentaram a
resposta e confundiria o novo recurso com o avaliador de seis dimensões.

## Objetivo

Permitir que o usuário faça uma pergunta única sobre um documento persistido e receba uma resposta
demo ou real baseada exclusivamente em um pacote congelado de evidências, com citações navegáveis e
exportação reproduzível.

## Escopo

### Incluído

- Runs persistidos e assíncronos de insight.
- Recuperação lexical e vetorial opcional, restrita a um documento.
- Pacote congelado com pergunta, revisão, perfil e origens.
- Geração demo determinística e Gemini real consentida.
- Validação estrita de citações e exportação JSON/Markdown.
- Tela própria com criação, acompanhamento, reabertura e resultado.

### Excluído

- Chat, streaming, busca entre documentos, OCR e novos formatos.
- Mudança na rubrica ou comparação automática de qualidade com a avaliação direta.
- Judge e alegações de acurácia sem corpus anotado.

## Requisitos

- **REQ-001:** criar um insight idempotente para documento, pergunta, modo de recuperação,
  quantidade de evidências e modo de geração explicitamente informados.
- **REQ-002:** recuperar somente unidades da revisão solicitada e congelar os trechos, origens,
  scores e perfil usados antes de publicar a resposta.
- **REQ-003:** o gerador deve receber somente a pergunta e o pacote congelado, tratar ambos como
  dados não confiáveis e citar IDs presentes nesse pacote.
- **REQ-004:** modo real exige capacidade disponível e confirmação explícita; modo demo permanece
  offline, determinístico e identificado como simulação.
- **REQ-005:** o run deve ter estados persistidos, reconciliar interrupções e nunca publicar pacote
  ou resposta parcial como sucesso.
- **REQ-006:** o usuário deve reabrir o run, inspecionar cada citação com página/unidade, copiar sua
  origem e exportar pergunta, configuração, pacote e resposta.
- **REQ-007:** falha ou desativação do perfil vetorial não pode acionar fallback lexical silencioso
  nem afetar avaliação direta e busca lexical.

## Critérios de aceite

- **AC-001 / REQ-001:** duas solicitações iguais com a mesma `Idempotency-Key` retornam o mesmo ID;
  reutilização da chave com parâmetros diferentes retorna conflito.
- **AC-002 / REQ-002, REQ-003:** cada citação do resultado resolve para uma evidência congelada da
  revisão; citação inexistente invalida a geração completa.
- **AC-003 / REQ-003, REQ-005:** zero hits encerra o run com `insufficient_evidence` e nenhuma
  chamada ao gerador ou resultado parcial.
- **AC-004 / REQ-004:** demo passa offline e real sem confirmação/chave não é enfileirado.
- **AC-005 / REQ-005:** reload preserva estados e resultado; reinício converte execução abandonada
  em `interrupted` sem repetir chamada externa.
- **AC-006 / REQ-006:** a tela conclui documento → pergunta → run → resposta → abertura e cópia da
  origem das fontes → exportação JSON/Markdown.
- **AC-007 / REQ-007:** perfil vetorial indisponível retorna falha explícita e o modo lexical segue
  utilizável.

## Contratos e dados

`POST /api/v1/insights` recebe:

```json
{
  "document_id": "uuid",
  "question": "Qual metodologia foi utilizada?",
  "retrieval_mode": "lexical",
  "retrieval_limit": 5,
  "mode": "demo",
  "confirm_external_processing": false
}
```

Pergunta: 1–200 caracteres após trim. Limite: 1–10. O resultado contém `evidence_package`,
`report` e `result_markdown`. O pacote usa IDs `E1..En`, preserva `unit_id`, página, trecho e score
e informa revisão e configuração da recuperação. A migração é aditiva e não altera dados atuais.

## Segurança e confiabilidade

Modo real envia ao provedor apenas pergunta e evidências congeladas. A interface informa esse
limite antes da confirmação. O worker aplica o timeout vigente do LLM e o mesmo failover restrito a
quota da avaliação. Respostas estruturadas inválidas, citações externas, falhas de recuperação e
erros do provedor terminam como falha segura.

## Plano de implementação

1. Criar domínio, schema, migração e repositório de insights — REQ-001, REQ-002, REQ-005.
2. Criar adaptadores demo/Gemini e orquestração com validação — REQ-002–REQ-004.
3. Integrar fila ao worker e expor API — REQ-001, REQ-004, REQ-005, REQ-007.
4. Criar tela, polling, fontes e exportações — REQ-006.
5. Validar e reconciliar documentação canônica — todos.

## Plano de validação

| Critério | Evidência planejada | Resultado |
|---|---|---|
| AC-001 | testes de serviço/API/PostgreSQL | passou em contêineres, incluindo idempotência PostgreSQL |
| AC-002 | testes de domínio e serviço | passou offline |
| AC-003 | teste de worker sem hits | passou offline |
| AC-004 | testes API e adaptador demo | demo passou em contêineres; real opt-in pendente |
| AC-005 | testes de worker/repositório | passou com PostgreSQL, smoke e backup/restore |
| AC-006 | Vitest, build e walkthrough | 4 testes/15 totais, build, smoke e walkthrough passaram |
| AC-007 | testes de serviço/API | indisponibilidade/fallback passaram offline |

Evidência executada em 2026-09-16: `./scripts/test-containers.sh` passou com Ruff, 97 testes
backend, typecheck, ESLint, 15 testes frontend, build Vite, migrações PostgreSQL/pgvector, smoke de
avaliação e insight, backup/restore e reinício do worker. A primeira execução detectou que a frase
da fixture lexical continha termos não anotados; a consulta foi corrigida para `worker persistente`
e a suíte completa passou na repetição.

O walkthrough visual foi executado na mesma data com `agent-browser 0.37.1` e Chrome for Testing
153 contra a stack Docker local. A rota `/insights` carregou em desktop e viewport móvel de
390 × 844, sem erros de página ou console da aplicação e com zero violações/incompletudes no
axe-core. O fluxo pela interface criou um insight, acompanhou sua conclusão e exibiu resposta,
citação E1 e origem congelada; a reabertura pelo histórico e os controles de exportação também
ficaram disponíveis.

## Questões abertas

- Nenhuma decisão bloqueante. Comparação automática e qualidade semântica pertencem ao EV-05 e à
  validação RAG com corpus autorizado.

## Desvios

- Nenhum desvio de implementação. A especificação permanece `em-implementacao` somente até o teste
  real opt-in ser executado com uma credencial de provedor explicitamente disponibilizada.
