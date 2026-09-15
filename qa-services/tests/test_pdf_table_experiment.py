from app.experiments.pdfplumber_tables import PdfPlumberTableExtractor
from app.services.parser_service import ParserService
from tests.pdf_factory import tabular_pdf


def test_compares_text_baseline_with_structured_table_candidate() -> None:
    fixture = tabular_pdf()
    expected_literals = (
        "Indicador",
        "Valor",
        "Bolsas",
        "0",
        "Conceito",
        "—",
        "Observacao",
    )
    expected_cells = [
        (1, 1, 1, "Indicador"),
        (1, 1, 2, "Valor"),
        (1, 2, 1, "Bolsas"),
        (1, 2, 2, "0"),
        (1, 3, 1, "Conceito"),
        (1, 3, 2, "—"),
        (1, 4, 1, "Observacao"),
        (1, 4, 2, None),
    ]

    baseline = ParserService().extract_text(fixture)
    tables = PdfPlumberTableExtractor().extract(fixture)

    baseline_hits = sum(literal in baseline.text for literal in expected_literals)
    assert baseline_hits == len(expected_literals)

    assert len(tables) == 1
    table = tables[0]
    assert (table.page, table.table, table.row_count, table.column_count) == (1, 1, 4, 2)
    actual_cells = [
        (cell.page, cell.row, cell.column, cell.text) for cell in table.cells
    ]
    exact_matches = sum(
        actual == expected for actual, expected in zip(actual_cells, expected_cells)
    )

    assert len(actual_cells) == len(expected_cells)
    assert exact_matches == len(expected_cells)
