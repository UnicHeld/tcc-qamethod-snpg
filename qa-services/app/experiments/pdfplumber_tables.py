import io
from dataclasses import dataclass

import pdfplumber


@dataclass(frozen=True, slots=True)
class TableCell:
    page: int
    table: int
    row: int
    column: int
    text: str | None


@dataclass(frozen=True, slots=True)
class ExtractedTable:
    page: int
    table: int
    row_count: int
    column_count: int
    cells: tuple[TableCell, ...]


class PdfPlumberTableExtractor:
    """Candidato de laboratório; não é importado pelo fluxo de produção."""

    def extract(self, pdf_content: bytes) -> tuple[ExtractedTable, ...]:
        extracted: list[ExtractedTable] = []
        with pdfplumber.open(io.BytesIO(pdf_content)) as document:
            for page_number, page in enumerate(document.pages, start=1):
                for table_number, rows in enumerate(page.extract_tables(), start=1):
                    column_count = max((len(row) for row in rows), default=0)
                    cells = tuple(
                        TableCell(
                            page=page_number,
                            table=table_number,
                            row=row_number,
                            column=column_number,
                            text=self._normalize_cell(value),
                        )
                        for row_number, row in enumerate(rows, start=1)
                        for column_number, value in enumerate(row, start=1)
                    )
                    extracted.append(
                        ExtractedTable(
                            page=page_number,
                            table=table_number,
                            row_count=len(rows),
                            column_count=column_count,
                            cells=cells,
                        )
                    )
        return tuple(extracted)

    @staticmethod
    def _normalize_cell(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
