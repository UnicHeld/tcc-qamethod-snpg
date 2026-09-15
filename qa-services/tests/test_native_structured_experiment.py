import pytest

from app.experiments.native_structured import (
    NativeStructuredExtractor,
    StructuredDocumentError,
    StructuredSourceFormat,
    StructuredValueKind,
)


def test_extracts_csv_without_inferring_types_or_conflating_missing_values() -> None:
    content = (
        "Indicador,Valor,Ativo,Observacao\n"
        "Bolsas,0,true,\n"
        "Conceito,—,false\n"
    ).encode()

    document = NativeStructuredExtractor().extract(
        content, StructuredSourceFormat.CSV
    )

    assert document.record_count == 2
    assert document.field_names == ("Indicador", "Valor", "Ativo", "Observacao")
    assert [
        (
            field.record,
            field.line,
            field.column,
            field.field,
            field.present,
            field.value,
            field.kind,
        )
        for field in document.fields
    ] == [
        (1, 2, 1, "Indicador", True, "Bolsas", StructuredValueKind.STRING),
        (1, 2, 2, "Valor", True, "0", StructuredValueKind.STRING),
        (1, 2, 3, "Ativo", True, "true", StructuredValueKind.STRING),
        (1, 2, 4, "Observacao", True, "", StructuredValueKind.STRING),
        (2, 3, 1, "Indicador", True, "Conceito", StructuredValueKind.STRING),
        (2, 3, 2, "Valor", True, "—", StructuredValueKind.STRING),
        (2, 3, 3, "Ativo", True, "false", StructuredValueKind.STRING),
        (2, 3, 4, "Observacao", False, None, StructuredValueKind.MISSING),
    ]


def test_extracts_json_preserving_scalar_types_and_missing_fields() -> None:
    content = br"""[
      {"indicador": "Bolsas", "valor": 0, "ativo": true, "observacao": null},
      {"indicador": "Conceito", "valor": "\u2014", "ativo": false}
    ]"""

    document = NativeStructuredExtractor().extract(
        content, StructuredSourceFormat.JSON
    )

    assert document.record_count == 2
    assert document.field_names == ("indicador", "valor", "ativo", "observacao")
    assert [
        (field.record, field.field, field.present, field.value, field.kind)
        for field in document.fields
    ] == [
        (1, "indicador", True, "Bolsas", StructuredValueKind.STRING),
        (1, "valor", True, 0, StructuredValueKind.INTEGER),
        (1, "ativo", True, True, StructuredValueKind.BOOLEAN),
        (1, "observacao", True, None, StructuredValueKind.NULL),
        (2, "indicador", True, "Conceito", StructuredValueKind.STRING),
        (2, "valor", True, "—", StructuredValueKind.STRING),
        (2, "ativo", True, False, StructuredValueKind.BOOLEAN),
        (2, "observacao", False, None, StructuredValueKind.MISSING),
    ]


@pytest.mark.parametrize(
    ("content", "source_format", "message"),
    [
        (b"a,a\n1,2\n", StructuredSourceFormat.CSV, "campos duplicados"),
        (b"a\n1,2\n", StructuredSourceFormat.CSV, "excede as colunas"),
        (b'{"a": 1, "a": 2}', StructuredSourceFormat.JSON, "chave duplicada"),
        (b'{"a": {"b": 1}}', StructuredSourceFormat.JSON, "aninhado"),
        (b'{"a": NaN}', StructuredSourceFormat.JSON, "número inválido"),
    ],
)
def test_rejects_ambiguous_or_unsupported_structured_content(
    content: bytes,
    source_format: StructuredSourceFormat,
    message: str,
) -> None:
    with pytest.raises(StructuredDocumentError, match=message):
        NativeStructuredExtractor().extract(content, source_format)
