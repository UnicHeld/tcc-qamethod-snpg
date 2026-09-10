import pytest

from app.services.parser_service import InvalidPdfError, ParserService, PdfWithoutTextError
from tests.pdf_factory import blank_pdf, synthetic_pdf


def test_extracts_text_and_locator_metadata_from_digital_pdf() -> None:
    result = ParserService().extract_text(synthetic_pdf("Metodo QA para o SNPG"))

    assert result.text == "Metodo QA para o SNPG"
    assert result.page_count == 1
    assert len(result.sha256) == 64


def test_rejects_invalid_signature() -> None:
    with pytest.raises(InvalidPdfError):
        ParserService().extract_text(b"conteudo invalido")


def test_distinguishes_pdf_without_text() -> None:
    with pytest.raises(PdfWithoutTextError, match="OCR"):
        ParserService().extract_text(blank_pdf())
