# Judge separado de pareceres

- **Status:** `implementado` nos modos demo offline e real opt-in; validação semântica pendente
- **Responsável:** a definir com o mantenedor
- **Última atualização:** 2026-09-16
- **System design:** [judge separado](../architecture/judge-runs-design.md)

## Problema e objetivo

A comparação atual mostra diferenças entre runs, mas não produz achados auditáveis. Este incremento
permite congelar um parecer concluído e suas evidências citadas, executar um judge demo ou um
segundo LLM e consultar um relatório separado, sem corrigir ou substituir o original.

## Escopo

Inclui domínio validado, snapshots do parecer e dos trechos citados, fila PostgreSQL, worker, API
idempotente, histórico, adaptadores demo/Gemini e exportação Markdown. Exclui correção automática,
ranking entre modelos, alegação de qualidade semântica e validação humana definitiva.

## Requisitos

- **REQ-001:** aceitar somente parecer concluído e congelar sua representação canônica e o texto
  exato de todas as evidências citadas antes do processamento.
- **REQ-002:** persistir judge em recurso separado, com estados, idempotência e reconciliação de
  execução interrompida.
- **REQ-003:** validar dimensões e evidências citadas por cada achado contra o snapshot fonte.
- **REQ-004:** o modo demo deve ser offline, determinístico e identificado como simulação.
- **REQ-005:** publicar resultado apenas de forma atômica após validação e nunca alterar o run ou
  parecer fonte.
- **REQ-006:** o modo real exige confirmação explícita, chave disponível, modelo permitido e um
  modelo de judge diferente daquele configurado para produzir o parecer.
- **REQ-007:** o provedor recebe somente o parecer congelado e os trechos citados; instruções nesses
  dados são tratadas como conteúdo não confiável. A reserva é tentada uma vez apenas após quota.

## Critérios de aceite

- **AC-001 / REQ-001, REQ-005:** run inexistente, incompleto ou sem resultado é rejeitado; o JSON
  de `evaluation_runs.report` permanece idêntico após a auditoria.
- **AC-002 / REQ-002:** repetição da mesma chave e solicitação retorna o mesmo ID; parâmetros
  diferentes geram conflito; reinício marca `running` como `interrupted`.
- **AC-003 / REQ-003:** achado com dimensão ou evidência inexistente invalida a geração completa.
- **AC-004 / REQ-004, REQ-006:** demo passa sem rede/chave; real sem consentimento ou configuração
  válida não é enfileirado; configuração com o mesmo modelo do avaliador é recusada.
- **AC-005 / REQ-005:** resultado contém hash e snapshot fonte, relatório separado e Markdown
  derivado somente depois de `succeeded`.
- **AC-006 / REQ-001, REQ-007:** o pacote persistido contém exatamente os IDs e textos citados, e
  o cliente falso comprova que esse pacote, não o documento completo, compõe a solicitação real.
- **AC-007 / REQ-006, REQ-007:** resposta real estruturada registra provedor, modelo, consumo e
  credencial `primary` ou `fallback`; fallback não ocorre para erros alheios à quota.

## Plano de implementação

1. Definir contratos, renderização e testes de domínio — REQ-003–REQ-005.
2. Adicionar migração, repositório idempotente e testes PostgreSQL — REQ-001, REQ-002, REQ-005.
3. Integrar worker, adaptadores demo/real e API — todos.
4. Expor criação, acompanhamento e achados na comparação visual — REQ-005.
5. Executar validação containerizada e reconciliar roadmap — todos.

## Questões abertas

Não há decisão bloqueante para uso funcional opt-in. O modelo concreto depende da allowlist e da
disponibilidade da conta. Qualidade semântica, limiares de aceitação e comparação entre modelos
continuam condicionados a corpus autorizado e amostra revisada por humanos.

## Evidências

Em 2026-09-16, `./scripts/test-containers.sh` passou com Ruff, 111 testes backend no PostgreSQL
17.11, typecheck, ESLint, 17 testes frontend, build Vite, smoke de parecer → judge → resultado,
backup/restore e reinício do worker. A suíte cobre snapshot e hash, evidências congeladas,
imutabilidade do parecer fonte, idempotência, reconciliação, referências inválidas, consentimento,
separação entre modelos, resposta estruturada, failover restrito a quota, polling da interface e
exportações. O cliente falso valida o protocolo real sem rede nem custo. A validação não mede
qualidade semântica do judge e não substitui o teste real opt-in do provedor.
