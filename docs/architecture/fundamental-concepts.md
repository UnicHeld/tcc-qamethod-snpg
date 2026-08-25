# Conceitos fundamentais

## Escopo do projeto

O TCC QA Method implementa um método automatizado de avaliação de qualidade para dissertações
de mestrado e teses de doutorado do SNPG. O sistema recebe um PDF, extrai o texto, consulta
uma base de conhecimento via RAG e gera uma análise estruturada em seis dimensões usando um LLM.

## Componentes

| Componente | Responsabilidade |
|---|---|
| `qa-services/` | API FastAPI: recebe PDFs, orquestra extração, RAG e geração |
| `qa-application/` | Interface React: upload de documento e exibição da avaliação em stream |
| `notebooks/` | Análise exploratória, validação estatística e experimentos de avaliação RAG |

## Dimensões de avaliação

O método avalia cada documento em seis dimensões, cada uma com nota de 0 a 10:

1. **Originalidade** — contribuição nova ao campo.
2. **Relevância** — impacto científico, tecnológico, cultural ou social.
3. **Metodologia** — rigor e adequação dos métodos empregados.
4. **Qualidade da redação** — clareza, coesão e normas acadêmicas.
5. **Estrutura** — organização e progressão lógica do texto.
6. **Interdisciplinaridade** — diálogo com outras áreas do conhecimento.

## Fluxo principal

```
PDF → extração de texto → (RAG: recuperação de contexto) → prompt + dimensões → Gemini → stream → cliente
```

Cada passo é responsabilidade de um serviço distinto em `qa-services/app/services/`. Routers não
contêm lógica de domínio.

## Limites do sistema

- O sistema não armazena documentos enviados; o PDF é processado em memória.
- O método é auxiliar: a nota final de banca é responsabilidade dos avaliadores humanos.
- O LLM avalia com base no texto extraído; qualidade de extração afeta diretamente o resultado.
