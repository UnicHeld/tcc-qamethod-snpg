import os
from io import BytesIO
from uuid import uuid4

import psycopg
import pytest
from pypdf import PdfReader, PdfWriter

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.core.migrations import apply_migrations
from app.services.parser_service import ParserService
from tests.pdf_factory import image_only_pdf, synthetic_pdf


@pytest.mark.database
def test_postgres_migrations_and_document_repository_are_idempotent() -> None:
    database_url = os.environ["DATABASE_URL"]
    apply_migrations(database_url)
    apply_migrations(database_url)
    repository = PostgresDocumentRepository(database_url)
    marker = uuid4().hex
    writer = PdfWriter()
    writer.add_page(
        PdfReader(BytesIO(synthetic_pdf(f"Documento PostgreSQL {marker}."))).pages[0]
    )
    writer.add_page(PdfReader(BytesIO(image_only_pdf())).pages[0])
    writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    parsed = ParserService().extract_text(output.getvalue())

    first = repository.save("fixture.pdf", parsed)
    try:
        second = repository.save("duplicado.pdf", parsed)
        reopened = repository.get(str(first.id))
        units = repository.list_units(str(first.id))
        pages = repository.list_pages(str(first.id))

        assert second.id == first.id
        assert reopened == first
        assert len(units) == 1
        assert units[0].document_id == first.id
        assert marker in units[0].text
        assert len(pages) == 3
        assert all(page.document_id == first.id for page in pages)
        assert [page.status for page in pages] == ["extracted", "ocr_candidate", "no_text"]
        assert pages[0].character_count == len(parsed.text)
        assert sum(item.id == first.id for item in repository.list_documents()) == 1
    finally:
        with psycopg.connect(database_url) as connection:
            connection.execute("DELETE FROM documents WHERE id = %s", (first.id,))
