# Baseline de recuperação vetorial local

- Data: 2026-09-15.
- Entregável: EV-02 do [roteiro de recuperação](../specs/prototype-recovery.md).
- Perfil: `intfloat/multilingual-e5-small`, 384 dimensões, chunk
  `document-unit-v1` de até 384 tokens com sobreposição de 64 tokens.

## Objetivo e fixture

Confirmar que o perfil local materializa e reutiliza embeddings, recupera uma unidade semanticamente
relacionada e mantém página/origem verificáveis. O smoke usa um PDF sintético de duas páginas:

1. entrevistas semiestruturadas, depoimentos e análise temática;
2. tabelas estatísticas, questionários e percentuais.

A consulta vetorial anotada é “Como os participantes foram ouvidos para interpretar seus relatos?”.
A página relevante esperada é a página 1. Uma consulta lexical por `entrevistas` funciona como
controle de admissão, persistência e proveniência.

## Resultado observado

Execução local containerizada em CPU, sem GPU, chave ou API de embeddings:

| Medida | Resultado |
|---|---:|
| Controle lexical, top-1 | página 1 |
| Recuperação vetorial fria, top-1 | página 1 |
| Recuperação vetorial quente, top-1 | página 1 |
| Recall@1 nesta única consulta anotada | 1,0 |
| Primeira consulta em volume novo, incluindo download/indexação | 44,907 s |
| Segunda consulta, reutilizando cache/índice | 0,034 s |
| Cache local após a execução | 273,6 MiB |

A resposta registrou modelo, dimensão e versão de chunk. A tela comparou resultados lexical e
vetorial em desktop e 390 × 844 px, sem erro de console nem violação WCAG A/AA detectada pelo
axe-core.

## Reprodução

O teste é opt-in porque a primeira execução baixa pesos para um volume local:

```bash
QA_VECTOR_TEST_CONFIRM=download-local-model ./scripts/test-vector-search-live.sh
```

O script usa projeto e volume Compose isolados, dados sintéticos e nenhuma credencial. A suíte
offline comum não baixa pesos.

## Limitações

Uma consulta sintética comprova integração e recuperabilidade, não qualidade generalizável. Não há
alegação de precisão sobre dissertações reais, comparação de modelos, consumo máximo de memória ou
desempenho em outro hardware. O score cosseno serve apenas à ordenação. Ampliar métricas exige um
corpus autorizado, várias consultas anotadas e revisão humana sem alterar simultaneamente o modelo,
o chunking e a rubrica.
