import os
from io import BytesIO
from uuid import uuid4

import psycopg
import pytest
from pypdf import PdfReader, PdfWriter

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.adapters.postgres_search import PostgresSearchRepository
from app.core.migrations import apply_migrations
from app.domain.search import EmbeddedChunk, EmbeddingProfile
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


@pytest.mark.database
def test_postgres_vector_index_is_reconstructible_and_scoped() -> None:
    database_url = os.environ["DATABASE_URL"]
    apply_migrations(database_url)
    document_repository = PostgresDocumentRepository(database_url)
    document = document_repository.save(
        "vetorial.pdf",
        ParserService().extract_text(
            multipage_pdf(
                "Pesquisa com entrevistas e análise qualitativa.",
                "Resultados numéricos de um levantamento quantitativo.",
            )
        ),
    )
    units = document_repository.list_units(str(document.id))
    profile = EmbeddingProfile(
        model="test/multilingual",
        dimension=384,
        chunk_version="test-v1",
        max_tokens=384,
        overlap_tokens=64,
    )
    first_vector = (1.0,) + (0.0,) * 383
    second_vector = (0.0, 1.0) + (0.0,) * 382
    chunks = (
        EmbeddedChunk(units[0].id, 1, 0, units[0].text, first_vector),
        EmbeddedChunk(units[1].id, 2, 0, units[1].text, second_vector),
    )
    repository = PostgresSearchRepository(database_url)

    try:
        assert repository.is_vector_indexed(str(document.id), profile) is False
        repository.replace_vector_index(str(document.id), profile, chunks)
        assert repository.is_vector_indexed(str(document.id), profile) is True

        hits = repository.search_vector(
            str(document.id), profile, first_vector, limit=2
        )

        assert [hit.page for hit in hits] == [1, 2]
        assert hits[0].score == pytest.approx(1.0)
        assert hits[1].score == pytest.approx(0.0)
    finally:
        with psycopg.connect(database_url) as connection:
            connection.execute("DELETE FROM documents WHERE id = %s", (document.id,))
