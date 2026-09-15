from io import BytesIO

import pytest
from pydantic import ValidationError
from pypdf import PdfReader, PdfWriter

from app.domain.evaluation import (
    Dimension,
    DimensionResult,
    EvaluationReport,
    render_markdown,
)
from app.services.parser_service import ParserService
from tests.pdf_factory import synthetic_pdf


def report_payload() -> dict:
    document = ParserService().extract_text(synthetic_pdf()).as_revision()
    return {
        "revision_sha256": document.sha256,
        "simulated": True,
        "title": "Parecer de teste",
        "summary": "Resumo de teste.",
        "dimensions": [
            {
                "dimension": dimension.value,
                "insufficient": False,
                "score": 0,
                "justification": "Exemplo simulado.",
                "evidence_ids": [document.units[0].id],
            }
            for dimension in Dimension
        ],
    }


@pytest.mark.parametrize("score", [-1, 11, float("nan"), float("inf"), True, "5"])
def test_rejects_invalid_scores(score: object) -> None:
    payload = report_payload()["dimensions"][0]
    payload["score"] = score
    with pytest.raises(ValidationError):
        DimensionResult.model_validate(payload)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra", "blank", "no_evidence"])
def test_rejects_invalid_reports(mutation: str) -> None:
    payload = report_payload()
    if mutation == "missing":
        payload["dimensions"].pop()
    elif mutation == "duplicate":
        payload["dimensions"][1] = payload["dimensions"][0]
    elif mutation == "extra":
        payload["aggregate_score"] = 5
    elif mutation == "blank":
        payload["dimensions"][0]["justification"] = "   "
    else:
        payload["dimensions"][0]["evidence_ids"] = []
    with pytest.raises(ValidationError):
        EvaluationReport.model_validate(payload)


def test_insufficiency_is_not_zero() -> None:
    payload = report_payload()["dimensions"][0]
    payload["insufficient"] = True
    with pytest.raises(ValidationError):
        DimensionResult.model_validate(payload)
    payload["score"] = None
    payload["evidence_ids"] = []
    assert DimensionResult.model_validate(payload).score is None


@pytest.mark.parametrize("foreign_revision", [False, True])
def test_render_rejects_unknown_evidence_or_revision(foreign_revision: bool) -> None:
    document = ParserService().extract_text(synthetic_pdf()).as_revision()
    payload = report_payload()
    if foreign_revision:
        payload["revision_sha256"] = "a" * 64
    else:
        payload["dimensions"][0]["evidence_ids"] = [f"{document.sha256}:page:99"]
    with pytest.raises(ValueError):
        render_markdown(EvaluationReport.model_validate(payload), document)


def test_render_is_ordered_and_labels_simulation() -> None:
    document = ParserService().extract_text(synthetic_pdf()).as_revision()
    payload = report_payload()
    payload["dimensions"].reverse()
    markdown = render_markdown(EvaluationReport.model_validate(payload), document)
    assert markdown.count("\n## ") == 6
    assert markdown.count("Nota simulada: 0.0") == 6
    assert markdown.index("Originalidade") < markdown.index("Interdisciplinaridade")
    assert "Simulado — sem inferência LLM" in markdown
    assert markdown.startswith("# Parecer de teste")


def test_page_units_keep_physical_page_numbers_and_stable_ids() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_page(PdfReader(BytesIO(synthetic_pdf())).pages[0])
    output = BytesIO()
    writer.write(output)
    first = ParserService().extract_text(output.getvalue()).as_revision()
    second = ParserService().extract_text(output.getvalue()).as_revision()
    assert first == second
    assert first.page_count == 2
    assert len(first.units) == 1
    assert first.units[0].page == 2
    assert first.units[0].id == f"{first.sha256}:page:2"
