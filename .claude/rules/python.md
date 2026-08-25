# Layer: Python

## Formatação e lint

- Usar Ruff; não reformatar fora do escopo.
- Manter imports válidos; remover código morto detectado por `E`, `W` e `F`.
- Usar nomes explícitos e type hints.

## Testes

- Framework: pytest.
- Mockar integrações externas no ponto de uso.
- Executar ruff e testes relevantes após mudanças Python.

## Convenções

- Preferir retornos antecipados a condicionais profundamente aninhadas.
- Separar regra de negócio de prompts, apresentação e infraestrutura.
- Não capturar exceções sem registrar contexto seguro ou aplicar fallback explícito.
