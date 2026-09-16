# Failover controlado entre credenciais Gemini gratuitas

- Status: `aceita`
- Data: 2026-09-13
- Escopo: adaptador Gemini real

## Contexto

O mantenedor disponibilizou uma chave principal e uma chave reserva pertencentes a projetos e contas
diferentes, ambos declarados no nível gratuito, para permitir testes quando a quota de um projeto se
esgotar. A API Gemini aplica quota por projeto, não por chave. Repetir indiscriminadamente uma chamada
pode duplicar transferência de conteúdo e consumo.

## Decisão

Aceitar `GEMINI_FALLBACK_API_KEY` como credencial opcional do backend. O adaptador tenta a reserva no
máximo uma vez e somente quando a tentativa principal termina com erro de quota (`429`). Timeout,
falha de transporte, resposta vazia ou JSON inválido encerram a execução sem failover.

O resultado registra `credential_slot` como `primary` ou `fallback`, sem guardar chave, conta ou ID de
projeto. As duas tentativas usam o mesmo modelo permitido, prompt e consentimento já confirmado para
o documento. Ausência da reserva preserva o comportamento atual de erro explícito.

## Consequências

- A reserva amplia apenas a disponibilidade dos testes; não garante gratuidade nem aumenta a quota de
  um mesmo projeto.
- Um documento pode ser enviado a duas contas Google após quota da primeira; essa possibilidade deve
  constar no consentimento da interface e no runbook.
- Não há failover para plano pago, outro modelo, demo ou outro provedor.
- Logs e exportações identificam o slot usado, nunca o segredo.
