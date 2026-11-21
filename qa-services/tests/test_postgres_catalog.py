import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from app.adapters.postgres_catalog import PostgresCatalogRepository
from app.adapters.postgres_documents import PostgresDocumentRepository
from app.core.config import Settings, get_settings
from app.core.migrations import apply_migrations
from app.domain.catalog import AcademicMetadata, CatalogFilters
from app.main import app
from app.services.catalog_service import CatalogEntryNotFoundError, CatalogRevisionConflictError
from app.services.parser_service import ParserService
from tests.pdf_factory import synthetic_pdf

pytestmark = pytest.mark.database


def pdf_pages(*texts):
    writer = PdfWriter()
    for text in texts:
        writer.add_page(PdfReader(BytesIO(synthetic_pdf(text))).pages[0])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture
def corpus():
    database_url = os.environ["DATABASE_URL"]
    apply_migrations(database_url)
    apply_migrations(database_url)
    documents = PostgresDocumentRepository(database_url)
    catalog = PostgresCatalogRepository(database_url)
    marker = uuid4().hex
    saved = []
    for index in range(4):
        texts = [f"Metodologia de pesquisa {marker} trabalho {index}."]
        if index == 0:
            texts.append("Metodologia metodologia de pesquisa na segunda pagina.")
        saved.append(
            documents.save(f"trabalho-{index}.pdf", ParserService().extract_text(pdf_pages(*texts)))
        )
    metadata = (
        AcademicMetadata(
            "Gestão", "thesis", 2023, "Gestão", "UFSC", marker, "Ana", "Joana", "Pedro"
        ),
        AcademicMetadata(
            "Engenharia", "dissertation", 2024, "Engenharia", "UFSC", marker, "Bruno", "Joana"
        ),
        AcademicMetadata(
            "Ano desconhecido",
            "thesis",
            institution="Outra",
            program=marker,
            author="Carla",
            advisor="Luiz",
        ),
    )
    entries = tuple(catalog.save(doc.id, meta, 0) for doc, meta in zip(saved, metadata))
    try:
        yield catalog, documents, saved, entries, marker
    finally:
        with psycopg.connect(database_url) as connection:
            connection.execute("DELETE FROM documents WHERE id = ANY(%s)", ([d.id for d in saved],))


def test_catalog_persists_reopens_and_rejects_stale_updates(corpus):
    catalog, documents, saved, entries, _ = corpus
    reopened = PostgresCatalogRepository(os.environ["DATABASE_URL"]).get(saved[0].id)
    assert reopened == entries[0]
    assert reopened.metadata_source == "manual"
    new_metadata = replace(reopened.metadata, title="Título revisado", publication_year=2025)
    updated = catalog.save(saved[0].id, new_metadata, 1)
    assert updated.metadata_revision == 2
    assert updated.metadata == new_metadata
    assert documents.get(str(saved[0].id)) == saved[0]
    for revision in (0, 1):
        with pytest.raises(CatalogRevisionConflictError):
            catalog.save(saved[0].id, reopened.metadata, revision)
    assert catalog.get(saved[0].id) == updated


def test_catalog_filters_all_fields_and_paginates_without_truncating_totals(corpus):
    catalog, _, saved, _, marker = corpus
    filtered = CatalogFilters(
        program=marker,
        institution="ufsc",
        document_type="thesis",
        year_from=2023,
        year_to=2023,
        area="gestão",
        author="ana",
        advisor="joana",
        coadvisor="pedro",
    )
    result = catalog.list_entries(filtered, 10, 0)
    assert [entry.document.id for entry in result.entries] == [saved[0].id]
    assert result.total == 1
    all_entries = catalog.list_entries(CatalogFilters(program=marker), 1, 0)
    second = catalog.list_entries(CatalogFilters(program=marker), 1, 1)
    assert all_entries.total == second.total == 3
    assert all_entries.entries[0].document.id != second.entries[0].document.id
    past_end = catalog.list_entries(CatalogFilters(program=marker), 10, 100)
    assert past_end.entries == () and past_end.total == 3
    for unknown in (
        CatalogFilters(program=marker, year_from=2025),
        CatalogFilters(program=marker, area="Gest"),
        CatalogFilters(program=marker, advisor="%"),
        CatalogFilters(program=marker, author="' OR TRUE --"),
    ):
        assert catalog.list_entries(unknown, 10, 0).total == 0
    known_years = catalog.list_entries(CatalogFilters(program=marker, year_to=2024), 10, 0)
    assert {entry.document.id for entry in known_years.entries} == {d.id for d in saved[:2]}


def test_catalog_searches_cross_document_with_filters_and_stable_pagination(corpus):
    catalog, _, saved, _, marker = corpus
    filters = CatalogFilters(program=marker)
    matches = catalog.search("metodologia", filters, 50, 0)
    assert matches.total_hits == 4 and matches.total_documents == 3
    assert {hit.entry.document.id for hit in matches.hits} == {d.id for d in saved[:3]}
    assert saved[3].id not in {hit.entry.document.id for hit in matches.hits}
    assert [hit.score for hit in matches.hits] == sorted(
        [hit.score for hit in matches.hits], reverse=True
    )
    pages = tuple(catalog.search("metodologia", filters, 1, offset).hits[0] for offset in range(4))
    assert pages == matches.hits
    past_end = catalog.search("metodologia", filters, 5, 100)
    assert past_end.hits == () and past_end.total_hits == 4
    assert past_end.total_documents == 3
    selected = catalog.search(
        "metodologia",
        CatalogFilters(program=marker, area="engenharia", year_from=2024, advisor="joana"),
        10,
        0,
    )
    assert [hit.entry.document.id for hit in selected.hits] == [saved[1].id]
    assert selected.total_hits == selected.total_documents == 1
    empty = catalog.search("termoquenaoexiste", filters, 10, 0)
    assert empty.hits == () and empty.total_hits == empty.total_documents == 0


def test_catalog_evidence_rejects_cross_document_and_uncataloged_sources(corpus):
    catalog, documents, saved, entries, _ = corpus
    unit = documents.list_units(str(saved[0].id))[1]
    evidence = catalog.get_evidence(saved[0].id, unit.id)
    assert evidence.entry == entries[0]
    assert evidence.page == 2 and evidence.text == unit.text
    with pytest.raises(CatalogEntryNotFoundError):
        catalog.get_evidence(saved[1].id, unit.id)
    with pytest.raises(CatalogEntryNotFoundError):
        catalog.get_evidence(saved[3].id, documents.list_units(str(saved[3].id))[0].id)


@pytest.mark.parametrize("initial_revision", [0, 1])
def test_catalog_concurrent_writes_have_one_winner(corpus, initial_revision):
    catalog, _, saved, entries, _ = corpus
    document = saved[3] if initial_revision == 0 else saved[0]

    def save(title):
        try:
            return catalog.save(
                document.id, replace(entries[0].metadata, title=title), initial_revision
            )
        except CatalogRevisionConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(save, ("Primeira edição", "Segunda edição")))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    assert catalog.get(document.id) == winners[0]
    assert winners[0].metadata_revision == initial_revision + 1


def test_catalog_http_flow_uses_persisted_sources_and_preserves_document_search(corpus):
    _, _, saved, _, marker = corpus
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url=os.environ["DATABASE_URL"]
    )
    try:
        with TestClient(app) as client:
            listing = client.get("/api/v1/catalog/documents", params={"program": marker})
            assert listing.status_code == 200
            assert listing.json()["total"] == 3
            search = client.post(
                "/api/v1/catalog/search",
                json={
                    "query": "metodologia",
                    "filters": {"program": marker, "year_from": 2024},
                },
            )
            assert search.status_code == 200
            hit = search.json()["hits"][0]
            assert hit["entry"]["document"]["id"] == str(saved[1].id)
            source = client.get(
                f"/api/v1/catalog/documents/{saved[1].id}/evidence/{hit['unit_id']}"
            )
            assert source.json()["entry"]["document"]["sha256"] == saved[1].sha256
            old_search = client.post(
                "/api/v1/search",
                json={
                    "document_id": str(saved[0].id),
                    "query": "metodologia",
                },
            )
            assert old_search.status_code == 200
            assert old_search.json()["document_id"] == str(saved[0].id)
            assert len(old_search.json()["hits"]) == 2
    finally:
        app.dependency_overrides.clear()
