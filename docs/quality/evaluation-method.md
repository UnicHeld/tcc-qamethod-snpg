# Método de avaliação

## Objetivo

Gerar uma análise crítica automatizada de dissertações de mestrado e teses de doutorado do SNPG,
estruturada nas dimensões exigidas pelos formulários de avaliação de banca.

## Dimensões e critérios

| Dimensão | Critérios principais |
|---|---|
| Originalidade | Contribuição nova; diferença em relação ao estado da arte |
| Relevância | Impacto científico, tecnológico, cultural ou social |
| Metodologia | Rigor, adequação e reprodutibilidade dos métodos |
| Qualidade da redação | Clareza, coesão, normas ABNT/acadêmicas |
| Estrutura | Organização, progressão lógica, completude das seções |
| Interdisciplinaridade | Diálogo com outras áreas; integração de perspectivas |

Cada dimensão recebe nota de 0 a 10. O método não produz nota final única.

## Prompt do avaliador

O template está em `qa-services/app/services/evaluation_service.py`.

Regras do prompt:
- Apresentar o título antes da análise.
- Analisar cada dimensão separadamente.
- Atribuir nota em negrito ao final de cada dimensão (`**Nota: X.X**`).
- Omitir informações pessoais (autor, orientador).
- Ser objetivo e imparcial; sem adjetivos ou advérbios de opinião pessoal.

Alterações no prompt devem ser validadas com o conjunto de documentos de referência antes de
serem integradas. Ver `docs/quality/rag-validation.md`.

## Limitações conhecidas

- A qualidade da análise depende da qualidade da extração de texto do PDF.
- PDFs com imagens, tabelas ou formatação complexa podem gerar extração incompleta.
- O LLM pode variar entre execuções mesmo com `temperature=0.1`.
