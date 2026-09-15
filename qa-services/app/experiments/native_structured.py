import csv
import io
import json
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias


StructuredValue: TypeAlias = str | int | float | bool | None


class StructuredDocumentError(Exception):
    """Entrada estruturada inválida para o contrato experimental."""


class StructuredSourceFormat(StrEnum):
    CSV = "csv"
    JSON = "json"


class StructuredValueKind(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    NULL = "null"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class StructuredField:
    record: int
    field: str
    present: bool
    value: StructuredValue
    kind: StructuredValueKind
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True, slots=True)
class StructuredDocument:
    source_format: StructuredSourceFormat
    record_count: int
    field_names: tuple[str, ...]
    fields: tuple[StructuredField, ...]


class NativeStructuredExtractor:
    """Baseline CSV/JSON nativo; não participa do fluxo de produção."""

    def extract(
        self, content: bytes, source_format: StructuredSourceFormat
    ) -> StructuredDocument:
        text = self._decode(content)
        if source_format is StructuredSourceFormat.CSV:
            return self._extract_csv(text)
        if source_format is StructuredSourceFormat.JSON:
            return self._extract_json(text)
        raise StructuredDocumentError("Formato estruturado não suportado.")

    @staticmethod
    def _decode(content: bytes) -> str:
        if not content:
            raise StructuredDocumentError("O documento estruturado está vazio.")
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise StructuredDocumentError(
                "O documento estruturado deve usar UTF-8."
            ) from error

    def _extract_csv(self, text: str) -> StructuredDocument:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        try:
            header = next(reader)
        except StopIteration as error:
            raise StructuredDocumentError("O CSV não contém cabeçalho.") from error
        except csv.Error as error:
            raise StructuredDocumentError("O CSV está inválido.") from error

        self._validate_header(header)
        fields: list[StructuredField] = []
        record_count = 0
        try:
            for record_count, row in enumerate(reader, start=1):
                if not row:
                    raise StructuredDocumentError(
                        f"A linha {reader.line_num} não contém colunas."
                    )
                if len(row) > len(header):
                    raise StructuredDocumentError(
                        f"A linha {reader.line_num} excede as colunas do cabeçalho."
                    )
                for column, field_name in enumerate(header, start=1):
                    present = column <= len(row)
                    fields.append(
                        StructuredField(
                            record=record_count,
                            line=reader.line_num,
                            column=column,
                            field=field_name,
                            present=present,
                            value=row[column - 1] if present else None,
                            kind=(
                                StructuredValueKind.STRING
                                if present
                                else StructuredValueKind.MISSING
                            ),
                        )
                    )
        except csv.Error as error:
            raise StructuredDocumentError("O CSV está inválido.") from error

        if record_count == 0:
            raise StructuredDocumentError("O CSV não contém registros.")
        return StructuredDocument(
            source_format=StructuredSourceFormat.CSV,
            record_count=record_count,
            field_names=tuple(header),
            fields=tuple(fields),
        )

    @staticmethod
    def _validate_header(header: list[str]) -> None:
        if not header or any(not field.strip() for field in header):
            raise StructuredDocumentError(
                "O cabeçalho CSV deve conter nomes de campo não vazios."
            )
        if len(set(header)) != len(header):
            raise StructuredDocumentError(
                "O cabeçalho CSV não pode conter campos duplicados."
            )

    def _extract_json(self, text: str) -> StructuredDocument:
        try:
            parsed = json.loads(
                text,
                object_pairs_hook=self._unique_object,
                parse_constant=self._reject_non_finite_number,
            )
        except (json.JSONDecodeError, StructuredDocumentError) as error:
            if isinstance(error, StructuredDocumentError):
                raise
            raise StructuredDocumentError("O JSON está inválido.") from error

        records = parsed if isinstance(parsed, list) else [parsed]
        if not records:
            raise StructuredDocumentError("O JSON não contém registros.")
        if any(not isinstance(record, dict) for record in records):
            raise StructuredDocumentError(
                "O JSON deve ser um objeto ou uma lista de objetos."
            )

        field_names = tuple(dict.fromkeys(field for record in records for field in record))
        if not field_names:
            raise StructuredDocumentError("Os objetos JSON não contêm campos.")

        fields: list[StructuredField] = []
        for record_number, record in enumerate(records, start=1):
            for field_name in field_names:
                present = field_name in record
                value = record.get(field_name)
                kind = self._value_kind(value) if present else StructuredValueKind.MISSING
                fields.append(
                    StructuredField(
                        record=record_number,
                        field=field_name,
                        present=present,
                        value=value,
                        kind=kind,
                    )
                )

        return StructuredDocument(
            source_format=StructuredSourceFormat.JSON,
            record_count=len(records),
            field_names=field_names,
            fields=tuple(fields),
        )

    @staticmethod
    def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise StructuredDocumentError(
                    f'O objeto JSON contém a chave duplicada "{key}".'
                )
            result[key] = value
        return result

    @staticmethod
    def _reject_non_finite_number(value: str) -> None:
        raise StructuredDocumentError(f'O JSON contém o número inválido "{value}".')

    @staticmethod
    def _value_kind(value: object) -> StructuredValueKind:
        if value is None:
            return StructuredValueKind.NULL
        if isinstance(value, bool):
            return StructuredValueKind.BOOLEAN
        if isinstance(value, int):
            return StructuredValueKind.INTEGER
        if isinstance(value, float) and math.isfinite(value):
            return StructuredValueKind.NUMBER
        if isinstance(value, str):
            return StructuredValueKind.STRING
        raise StructuredDocumentError(
            "JSON aninhado não é suportado no contrato experimental."
        )
