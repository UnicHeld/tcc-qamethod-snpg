# Compose como contrato de execução e testes offline

- Status: `aceita`.
- Data: 2026-09-13.
- [System design](../architecture/prototype-recovery-design.md).
- [Roteiro, requisitos e critérios de aceite](../specs/prototype-recovery.md).

## Contexto

API e interface já possuíam ambientes isolados no host, mas não havia um Compose e o Dockerfile do
backend estava vazio. Isso deixava a reprodução dependente da instalação local de Python, Node,
`uv` e npm e criava dois caminhos diferentes para testar localmente e na automação.

O perfil padrão precisa continuar funcionando sem credenciais. Testes reais de provedores são
opt-in, pois podem transferir documentos, consumir quota ou gerar custo.

## Decisão

O `compose.yaml` passa a ser o contrato executável da fatia local. Ele contém:

- imagens multi-stage separando runtime, desenvolvimento e testes de API e interface;
- API e interface publicadas apenas no loopback do host;
- interface estática servida por Nginx, com proxy de mesma origem em `/api`;
- serviços de teste offline, sem rede e sem credenciais;
- smoke test dos healthchecks, capabilities e entrega da SPA;
- override `compose.dev.yaml` para hot reload sem instalar runtimes no host.

O script `scripts/test-containers.sh` agrega configuração, builds, qualidade, testes e smoke test
em um projeto Compose isolado. O workflow de CI executa esse mesmo script, evitando lógica de
validação exclusiva da plataforma de automação.

Credenciais podem ser repassadas à API somente por variáveis do processo que inicia o Compose.
Elas não entram na imagem nem no frontend. O script de testes zera explicitamente as variáveis de
credencial, e testes de provedor real não pertencem ao workflow comum.

## Alternativas consideradas

| Alternativa | Benefícios | Custos e riscos | Resultado |
|---|---|---|---|
| Somente runtimes no host | Iteração direta e poucas camadas | Maior variação entre máquinas e CI | Mantida como alternativa documentada |
| Uma imagem para API, interface e testes | Um único artefato | Mistura processos, ferramentas e dependências de desenvolvimento | Descartada |
| Compose com targets por responsabilidade | Mesmo contrato local/CI e imagens finais menores | Mais estágios e tempo no primeiro build | Escolhida |
| Testes reais na CI padrão | Detecta mudanças do provedor | Requer segredo/rede e pode consumir quota ou dados | Descartada |

## Consequências

- O primeiro build precisa baixar imagens e dependências; builds seguintes usam cache.
- Alterações em manifests exigem rebuild, enquanto código usa hot reload no override de desenvolvimento.
- A suíte atual cobre unidade, contrato/componente e smoke HTTP, mas ainda não automatiza um fluxo
  completo em navegador; isso deve entrar quando os fluxos persistentes da F3 estabilizarem.
- A extensão pgvector será adicionada ao serviço PostgreSQL existente somente quando a F5 definir
  migração, índice e teste de indisponibilidade. Serviços opcionais de OCR seguem condicionados ao
  perfil e ao healthcheck correspondentes; existência no Compose não publica uma capacidade.

## Reavaliar esta decisão quando

O laboratório exigir GPU, múltiplas arquiteturas de CPU, execução remota, volumes persistentes com
backup ou uma topologia diferente do monólito modular local.
