# Continuar o Question Answering do TCC com a infraestrutura pós-TCC

- Status: `aceita`.
- Data: 2026-11-20.
- Origem: decisão do mantenedor de preservar a ideia original do TCC com as novas implementações.
- Alcance: direção do produto e responsabilidades das capacidades. A decisão de 2026-11-20
  alterou somente documentação; a primeira implementação do acervo em 2026-11-21 está vinculada abaixo.
- Contexto: [TCC de 2024](../history/tcc-2024.md) e [evolução pós-TCC](../history/post-tcc-2026.md).

## Contexto

O TCC propõe Question Answering sobre uma coleção de teses e dissertações para apoiar a
exploração da produção e a tomada de decisão em PPGs. O serviço de avaliação direta já existia
no protótipo, mas não define sozinho o objetivo acadêmico.

A retomada em 2026 tornou esse serviço o centro de um laboratório de análise documental e
acrescentou persistência, recuperação, evidências e judge. A base técnica evoluiu, enquanto os
contratos de busca e insights permaneceram restritos a um documento. São avanços aproveitáveis,
mas ainda não entregam consulta ao acervo, filtros acadêmicos e síntese entre trabalhos.

## Decisão

**O objetivo principal do projeto é responder perguntas sobre um acervo de teses e dissertações,
recuperando trabalhos e evidências para produzir sínteses e análises úteis à gestão de PPGs.**
QA significa Question Answering. A avaliação acadêmica individual e o judge permanecem como
serviços complementares e não passam a definir o significado de QA nem o critério principal de
conclusão do produto.

A continuidade preserva a finalidade do TCC e aproveita a implementação pós-TCC:

1. **Acervo e metadados:** orientar a evolução para uma coleção consultável com título, tipo,
   ano, área e autoria/orientação, com origem verificável dos campos. A omissão de dados pessoais
   no parecer individual não impede sua utilização autorizada como metadados de consulta.
2. **Recuperação:** permitir encontrar trabalhos e evidências entre documentos, combinando
   consulta semântica/lexical e filtros acadêmicos. O resultado deve identificar documento,
   revisão e localizador da fonte.
3. **Resposta:** sintetizar os documentos recuperados para a pergunta e distinguir resposta,
   fontes e limites da evidência. Comparar áreas ou períodos não autoriza inferir tendências de
   todo o PPG a partir de uma amostra ou seleção incompleta.
4. **Infraestrutura:** reutilizar FastAPI, React/Vite, PostgreSQL/pgvector, embeddings locais,
   filas, worker, pacotes congelados, histórico, exportações, Compose e testes. Modelos e
   bibliotecas do estudo não são requisitos de identidade do método.
5. **Serviços complementares:** preservar avaliação direta e judge, seus dados e contratos.
   O judge atual critica pareceres; não é validação já implementada das respostas de QA.
6. **Validação:** avaliar recuperação e respostas com consultas anotadas e revisão humana,
   separadamente dos testes de contrato e da avaliação das seis dimensões. Os resultados do
   estudo de 2024 não são herdados pelo código novo.

As regras de processamento local, consentimento para inferência externa, custos explícitos e
simulação identificada continuam vigentes. A necessidade de interpretar perguntas e filtros não
impõe reintroduzir LangChain, agentes autônomos, nuvem ou um segundo banco vetorial.

## Estado atual e sequência de evolução

A arquitetura implementada está nos [conceitos fundamentais](../architecture/fundamental-concepts.md).
Na aceitação desta ADR, as APIs de busca e insights eram limitadas por `document_id`.
Em 2026-11-21, o [acervo acadêmico](../specs/academic-catalog.md) acrescentou um contrato separado
de catálogo e busca lexical entre documentos. Busca vetorial e geração anteriores continuam por
documento. A [evolução do produto](../specs/product-evolution.md) distingue essa primeira entrega
das capacidades ainda planejadas.

O próximo trabalho de produto deve organizar entregáveis de valor nesta sequência:

| Entregável | Resultado para o usuário | Demonstração e critério de conclusão | Limites |
|---|---|---|---|
| Encontrar trabalhos no acervo — primeira entrega disponível | Consultar a coleção e combinar assunto com filtros acadêmicos | Admitir uma pequena coleção autorizada, consultar ano/área/orientador e abrir trabalhos e evidências corretos; verificar inclusão e exclusão dos filtros | Cadastro manual e busca lexical; sem síntese nem ingestão automática de repositórios |
| Obter síntese entre trabalhos | Fazer uma pergunta e receber análise baseada em diferentes documentos | Consultar a coleção, recuperar trabalhos e abrir cada fonte da resposta; verificar citações, insuficiência e respeito aos filtros | Não implica chat com memória nem cobertura de todo o SNPG |
| Verificar utilidade para o PPG | Conhecer a qualidade e os limites das consultas e sínteses | Executar consultas anotadas em corpus autorizado e revisar recuperação, fundamentação e utilidade das respostas | Não atribui validade geral a partir de fixtures ou do resultado histórico do TCC |

Antes de implementar esses entregáveis, produzir system design e especificação conforme o
[processo vigente](../processes/spec-driven-development.md). Devem ser definidos os contratos da
coleção, metadados e sua proveniência, filtros, seleção/versionamento do corpus, integridade das
evidências e critérios de validação. Nenhum endpoint, schema ou migração novos são fixados por
esta ADR.

Os IDs F0–F7 e EV-01–EV-06 dos documentos de recuperação permanecem como rastreabilidade das
entregas pós-TCC. Eles não devem ser renumerados nem tratados como se já cobrissem esses novos
entregáveis sobre o acervo. As pendências existentes continuam registradas, com prioridade
reavaliada em função do objetivo principal.

## Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Manter avaliação individual como finalidade principal | Descartada: não preserva o problema e o público centrais do TCC |
| Retornar integralmente ao código, modelos e infraestrutura de 2024 | Descartada: perde os avanços de reprodução, operação e rastreabilidade sem necessidade para manter o método |
| Continuar Question Answering sobre o acervo com a base pós-TCC | Escolhida: preserva a proposta acadêmica e aproveita as implementações recentes |

## Consequências

- Documentação separa evidência histórica, funcionamento atual e direção de evolução.
- Consulta ao acervo e síntese entre trabalhos passam a orientar as próximas entregas.
- A mudança requer futura ampliação de contratos e persistência; persistir documentos e unidades
  individualmente ou demonstrar um insight não basta para declarar continuidade funcional completa do TCC.
- Notebooks continuam arquivados conforme a
  [decisão existente](archive-poc-notebooks.md); novos experimentos serão reproduzíveis no produto.
- Permanecem as decisões de [PostgreSQL](postgresql-local-persistence.md) e
  [recuperação vetorial local](local-vector-retrieval.md). A preservação do método não exige
  reativar Qdrant/OpenAI legados.
- Esta decisão substitui a prioridade centrada em avaliação individual do roteiro de recuperação,
  sem revogar seus contratos implementados nem autorizar mudanças destrutivas.
