from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter

from app.domain.documents import PageExtractionStatus
from app.services.parser_service import InvalidPdfError, ParserService, PdfWithoutTextError
from tests.pdf_factory import blank_pdf, image_only_pdf, synthetic_pdf


def test_extracts_text_and_locator_metadata_from_digital_pdf() -> None:
    result = ParserService().extract_text(synthetic_pdf("Metodo QA para o SNPG"))

    assert result.text == "Metodo QA para o SNPG"
    assert result.page_count == 1
    assert len(result.sha256) == 64
    assert len(result.units) == 1
    assert result.units[0].id == f"{result.sha256}:page:1"
    assert result.units[0].page == 1
    assert result.units[0].text == result.text
    assert len(result.pages) == 1
    assert result.pages[0].status is PageExtractionStatus.EXTRACTED
    assert result.pages[0].character_count == len(result.text)
    assert result.pages[0].has_images is False


def test_rejects_invalid_signature() -> None:
    with pytest.raises(InvalidPdfError):
        ParserService().extract_text(b"conteudo invalido")


def test_distinguishes_pdf_without_text() -> None:
    with pytest.raises(PdfWithoutTextError, match="nem imagem raster"):
        ParserService().extract_text(blank_pdf())


def test_identifies_image_only_pdf_as_ocr_candidate() -> None:
    with pytest.raises(PdfWithoutTextError, match=r"1 página\(s\) candidata\(s\) a OCR"):
        ParserService().extract_text(image_only_pdf())


def test_classifies_every_physical_page_without_inventing_text() -> None:
    writer = PdfWriter()
    writer.add_page(PdfReader(BytesIO(synthetic_pdf("Página digital"))).pages[0])
    writer.add_page(PdfReader(BytesIO(image_only_pdf())).pages[0])
    writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)

    result = ParserService().extract_text(output.getvalue())

    assert [page.page for page in result.pages] == [1, 2, 3]
    assert [page.status for page in result.pages] == [
        PageExtractionStatus.EXTRACTED,
        PageExtractionStatus.OCR_CANDIDATE,
        PageExtractionStatus.NO_TEXT,
    ]
    assert len(result.units) == 1
    assert result.units[0].page == 1
