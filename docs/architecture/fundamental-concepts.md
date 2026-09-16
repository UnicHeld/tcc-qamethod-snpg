# Conceitos fundamentais

- Estado da aplicação: F1/F2, laboratório persistente F3a–F3d, extração experimental F4a–F4c,
  buscas EV-01/EV-02, implementação offline do insight RAG EV-03 e judge demo/real opt-in do EV-05
  até 2026-09-16; qualidade semântica do judge permanece pendente.

## Escopo do projeto

O TCC QA Method implementa um método automatizado de avaliação de qualidade para dissertações
de mestrado e teses de doutorado do SNPG. Na fatia ativa, o sistema recebe um PDF digital, extrai
o texto e produz uma análise direta em seis dimensões por simulação identificada ou por LLM
externo autorizado. RAG permanece experimental e não participa desse avaliador.

## Componentes

| Componente | Responsabilidade |
|---|---|
| `qa-services/` | API FastAPI: admite PDFs, busca unidades e processa avaliações/insights em worker local |
| `qa-application/` | Interface React/Vite: upload, busca, insights, histórico, comparação e exportação local |
| PostgreSQL | Metadados, unidades, índices, filas, pacotes de evidências, resultados e erros persistidos |
| pgvector | Extensão opcional do PostgreSQL para embeddings locais reconstruíveis |
| `notebooks/` | Arquivo histórico da POC; não integra produto, build, testes ou métricas vigentes |

## Dimensões de avaliação

O método avalia cada documento em seis dimensões, cada uma com nota de 0 a 10:

1. **Originalidade** — contribuição nova ao campo.
2. **Relevância** — impacto científico, tecnológico, cultural ou social.
3. **Metodologia** — rigor e adequação dos métodos empregados.
4. **Qualidade da redação** — clareza, coesão e normas acadêmicas.
5. **Estrutura** — organização e progressão lógica do texto.
6. **Interdisciplinaridade** — diálogo com outras áreas do conhecimento.

## Fluxo principal

```text
PDF digital → PostgreSQL → avaliação persistida → worker → parecer direto
                         ├→ busca lexical/vetorial → trechos com página e origem
                         └→ insight persistido → worker → pacote congelado → resposta citável
```

O router traduz HTTP e erros; parser, regras do prompt e adaptadores ficam nos serviços. O cliente
Gemini é criado sob demanda somente no modo real. A API e o worker usam conexões PostgreSQL
independentes; o desenho modular completo continua no
[desenho de recuperação](prototype-recovery-design.md).

## Limites do sistema

- Notebooks e suas dependências não são componentes do sistema; novos experimentos devem ser
  automatizados no componente responsável.
- `POST /api/v1/documents` persiste metadados e unidades extraídas no PostgreSQL; o PDF original ainda
  não é armazenado. A rota provisória `/evaluation/upload` continua processando apenas em memória.
- `POST /api/v1/runs` enfileira uma avaliação de documento persistido; a interface acompanha e
  reabre o run por seu ID.
- `POST /api/v1/insights` enfileira pergunta e configuração; o worker congela a recuperação antes
  da geração e só publica citações válidas contra o pacote.
- Backup/restore cobre o PostgreSQL; o PDF original ainda não faz parte desse artefato porque não é
  armazenado pelo sistema.
- PDF sem texto exige OCR, que ainda não está habilitado.
- A F4a sinaliza páginas com texto, candidatas a OCR e sem texto detectado; esses sinais não são
  afirmações de legibilidade ou vazio semântico.
- O resultado demo é simulado e não mede qualidade acadêmica.
- Buscas lexical e vetorial e o insight RAG são recursos separados do avaliador direto; o EV-03
  não altera a rubrica nem comprova correção semântica sem corpus e revisão humana.
- O método é auxiliar: a nota final de banca é responsabilidade dos avaliadores humanos.
- O LLM avalia com base no texto extraído; qualidade de extração afeta diretamente o resultado.
