# Baseline experimental de extração nativa CSV/JSON

- Status: validado offline em fixtures sintéticas; não integrado à API.
- Data da medição: 2026-09-15.
- Escopo: baseline experimental F4c de extração estruturada nativa.

## Objetivo e contrato

O experimento verifica se CSV e JSON podem ser lidos pela biblioteca padrão do Python sem LLM,
rede ou inferência silenciosa de conteúdo. Cada valor mantém presença, tipo e localizador próprios:

- CSV: registro, linha física, coluna e nome do campo; todos os valores presentes são strings;
- JSON: registro e nome do campo; valores escalares preservam o tipo declarado no documento;
- ambos distinguem campo ausente de um valor presente vazio ou nulo.

CSV exige cabeçalho não vazio e sem duplicatas. JSON aceita um objeto ou uma lista não vazia de
objetos escalares; objetos/listas aninhados permanecem fora deste primeiro contrato.

## Resultado

O ambiente containerizado usa Python 3.12.14. A implementação depende somente de `csv`, `json` e
outros módulos da biblioteca padrão.

| Medida | Referência | Resultado |
|---|---:|---:|
| Exact match CSV | 8 campos localizados | 8/8 (100%) |
| Exact match JSON | 8 campos tipados | 8/8 (100%) |
| Falhas explícitas | 5 casos | 5/5 (100%) |
| Coerções implícitas | nenhuma permitida | nenhuma observada |

As fixtures comprovam as distinções entre `""` e ausente no CSV e entre `null`, ausente, `0`,
`false`, string e travessão no JSON. Os casos negativos cobrem cabeçalho CSV duplicado, linha CSV
excedente, chave JSON duplicada, valor JSON aninhado e número não finito.

Reprodução focal:

```bash
docker compose --profile test run --rm backend-tests \
  pytest -p no:cacheprovider tests/test_native_structured_experiment.py
```

## Limitações e próxima integração

O experimento não cobre autodetecção de delimitador/encoding, JSON Lines, objetos aninhados,
streaming de arquivos grandes, schemas específicos do SNPG ou inferência de datas/números em CSV.
Esses comportamentos exigem contratos separados e não devem ser inferidos a partir desta fixture.

CSV/JSON ainda não são aceitos pelos endpoints. O modelo persistente vigente exige página física;
atribuir uma página artificial aos registros destruiria a semântica do localizador. Antes da
integração, `DocumentUnit` e o schema PostgreSQL devem receber localizadores discriminados e uma
migração compatível com as unidades PDF existentes.
