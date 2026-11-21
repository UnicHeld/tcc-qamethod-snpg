# Evolução do produto: do acervo local ao serviço nacional

- **Última atualização:** 2026-11-21
- **Direção:** [Question Answering do TCC](../decisions/restore-question-answering-focus.md)

A ordem combina complexidade crescente com dependências. Cada entrega precisa de demonstração
ponta a ponta, design, especificação e validação próprios antes de ser declarada concluída.
Estimativas são relativas à base atual, não promessa de prazo ou capacidade de produção.

| Ordem | Entrega e usuário/problema | Resultado e demonstração de aceite | Complexidade | Estado e limites |
|---|---|---|---|---|
| 1 | Acervo consultável para quem explora um PPG | Admitir/cadastrar PDFs, consultar assunto com filtros e abrir a fonte de cada resultado | Baixa–média | [Implementado e validado na automação local](academic-catalog.md); coleção local, metadados manuais e busca lexical; browser validado; Compose pendente |
| 2 | Recuperação semântica da coleção | Encontrar trabalhos relacionados sem repetição literal; medir ganho contra a busca lexical e inspecionar cobertura do índice | Média | Planejado; indexação assíncrona/versionada e ausência de fallback silencioso |
| 3 | Síntese entre trabalhos para perguntas sobre o PPG | Fazer pergunta com filtros, obter resposta com diferentes fontes congeladas e verificar insuficiência de evidência | Média–alta | Planejado; reutilizar filas, consentimento e pacotes, sem atribuir representatividade a amostras |
| 4 | Qualidade demonstrada para coordenadores de PPG | Executar consultas anotadas em corpus autorizado e revisar recuperação, citações e utilidade | Média–alta | Planejado; métricas históricas do TCC não validam automaticamente a versão nova |
| 5 | Atualização automática de um repositório institucional | Sincronizar uma fonte autorizada, reprocessar alterações e mostrar falhas/cobertura sem duplicar trabalhos | Alta | Planejado; definir contrato do conector, direitos de acesso, deduplicação e proveniência |
| 6 | Leitura de PDFs extensos e conteúdo multimodal | Recuperar texto, tabelas e figuras com localização verificável em documentos de teste | Alta | Planejado; avaliar parser/OCR e provedor opt-in, limites/custos atuais e corpus representativo |
| 7 | Serviço para universidades contratantes | Dois clientes usam acervos isolados, administram acesso e acompanham limites/uso | Alta | Planejado; autenticação, autorização, isolamento, auditoria, quotas, backup e operação antecedem exposição pública |
| 8 | Painel institucional com temas e cobertura | Ver temas/grupos de pesquisa e evolução de uma universidade, rastreando amostra, método e fontes | Alta | Planejado; clusters são agrupamentos analíticos, não classificação institucional oficial |
| 9 | Cobertura nacional e comparação entre instituições | Integrar fontes nacionais e institucionais, deduplicar, atualizar e mostrar cobertura e falhas por instituição | Muito alta | Planejado; ingestão incremental, filas, observabilidade, governança e custo; sem promessa de completude automática |

Implantar a etapa 1 não implica que autenticação, coleta nacional, clusters ou SaaS estejam
prontos. A integração com um fornecedor específico ou com notebooks externos depende de contrato
e viabilidade verificados no momento da implementação; não constitui premissa do método.
