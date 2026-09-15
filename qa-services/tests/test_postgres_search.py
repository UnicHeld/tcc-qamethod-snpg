import os
from io import BytesIO
from uuid import uuid4

import psycopg
import pytest
from pypdf import PdfReader, PdfWriter

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.adapters.postgres_search import PostgresSearchRepository
from app.core.migrations import apply_migrations
from app.services.parser_service import ParserService
from tests.pdf_factory import synthetic_pdf


def multipage_pdf(*page_texts: str) -> bytes:
    writer = PdfWriter()
    for text in page_texts:
        writer.add_page(PdfReader(BytesIO(synthetic_pdf(text))).pages[0])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.database
def test_postgres_lexical_search_is_scoped_and_deterministically_ordered() -> None:
    database_url = os.environ["DATABASE_URL"]
    apply_migrations(database_url)
    document_repository = PostgresDocumentRepository(database_url)
    marker = uuid4().hex
    selected = document_repository.save(
        "selecionado.pdf",
        ParserService().extract_text(
            multipage_pdf(
                f"Contexto geral {marker}.",
                "Metodologia verificável com protocolo explícito.",
                "Metodologia e metodologia com evidências reproduzíveis.",
            )
        ),
    )
    other = document_repository.save(
        "outro.pdf",
        ParserService().extract_text(
            synthetic_pdf("Metodologia metodologia metodologia de outro documento.")
        ),
    )

    try:
        hits = PostgresSearchRepository(database_url).search_lexical(
            str(selected.id), "metodologia", 10
        )

        assert [hit.page for hit in hits] == [3, 2]
        assert all(hit.document_id == selected.id for hit in hits)
        assert all(marker not in hit.text for hit in hits)
        assert hits[0].score > hits[1].score > 0
    finally:
        with psycopg.connect(database_url) as connection:
            connection.execute(
                "DELETE FROM documents WHERE id IN (%s, %s)",
                (selected.id, other.id),
            )
