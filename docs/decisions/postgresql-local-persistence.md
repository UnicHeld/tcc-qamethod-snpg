# PostgreSQL para persistência local do laboratório

- Status: `aceita`
- Data: 2026-09-13; ampliada para recuperação vetorial em 2026-09-15
- Escopo: F3 e F5 do roteiro de recuperação

## Contexto

A proposta inicial usava SQLite para reduzir o número de processos locais. O mantenedor optou por
PostgreSQL antes do início da persistência, quando ainda não existem dados de produto a migrar. A F3
precisa guardar documentos, unidades, runs e resultados com integridade, permitir um worker separado
e continuar executável localmente sem contratar infraestrutura.

## Decisão

Usar PostgreSQL 17.11 no Compose como fonte de metadados, estados, unidades extraídas e resultados.
O backend acessa o banco com `psycopg` 3 e migrações SQL incrementais próprias, executadas antes da
API. A primeira fatia persiste documentos e unidades; runs e worker reutilizarão a mesma fronteira.

O perfil local usa credenciais de desenvolvimento não secretas dentro da rede privada do Compose e
aceita `DATABASE_URL` no backend para outros ambientes. PostgreSQL não é publicado no host por
padrão. Testes de persistência usam uma instância isolada no Compose, sem APIs externas.

Na F5, o mesmo PostgreSQL receberá a extensão pgvector e armazenará embeddings versionados das
unidades documentais. Os vetores são índices derivados e reconstruíveis, vinculados por chave
estrangeira à unidade fonte; PostgreSQL continua sendo a única fonte de verdade. Modelo, dimensão,
versão do chunk e parâmetros de recuperação fazem parte do registro do índice. A ativação ocorrerá
por nova migração, sem modificar migrações já aplicadas.

A busca lexical permanece disponível como baseline e fallback. Falha ou ausência da extensão
vetorial não pode impedir admissão de documentos, avaliação direta ou modo demo. A imagem PostgreSQL
com pgvector, a estratégia de índice e seus limites serão fixados e medidos na implementação da F5.

## Consequências

- A stack padrão passa a ter um terceiro serviço e exige healthcheck do banco.
- Concorrência, transações e separação futura de API/worker não dependem de trocar o banco.
- Metadados, unidades e embeddings podem manter integridade transacional sem sincronização com um
  segundo banco ou volume de dados.
- O schema é versionado; migrações aplicadas não são reescritas e mudanças destrutivas exigem backup.
- O runtime do banco passa a depender de uma distribuição compatível com pgvector quando o perfil
  vetorial for ativado; upgrades do PostgreSQL e da extensão precisam ser testados em conjunto.
- Não será introduzido ORM nesta fatia: SQL explícito mantém o escopo e as dependências pequenos.
- Arquivos originais e artefatos grandes continuam fora do banco; o armazenamento gerenciado será
  detalhado antes de ser implementado.

## Alternativas descartadas

- **SQLite:** menor operação local, mas deixa uma troca de banco para depois da criação de runs e do
  worker. Foi substituído por decisão explícita do mantenedor antes de haver dados persistidos.
- **PostgreSQL gerenciado:** não atende ao requisito de execução sem contratação e não é necessário
  no laboratório local.
- **Qdrant separado:** atendia à POC vetorial, mas duplicaria operação, backup e sincronização para
  o volume previsto; pgvector mantém a recuperação próxima das unidades e filtros relacionais.
- **ORM + Alembic imediatamente:** adiciona abstrações sem necessidade para o primeiro schema; pode
  ser reavaliado se o número de agregados e consultas justificar.
