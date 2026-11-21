from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.domain.catalog import (
    AcademicMetadata,
    CatalogEntry,
    CatalogEvidence,
    CatalogMatch,
    CatalogMatches,
    CatalogPage,
)
from app.domain.documents import StoredDocument
from app.main import app
from app.routers.catalog import get_catalog_repository
from app.services.catalog_service import (
    CatalogEntryNotFoundError,
    CatalogRevisionConflictError,
)
from app.services.document_service import DocumentNotFoundError, DocumentRepositoryError


class FixtureCatalogRepository:
    def __init__(self):
        self.document = StoredDocument(uuid4(), "fixture.pdf", "a" * 64, 2, 1000, datetime.now(UTC))
        self.entry = None
        self.last_search = None

    def save(self, document_id, metadata, expected_revision):
        if document_id != self.document.id:
            raise DocumentNotFoundError("Documento não encontrado.")
        revision = self.entry.metadata_revision if self.entry else 0
        if expected_revision != revision:
            raise CatalogRevisionConflictError("Reabra o cadastro antes de salvar.")
        self.entry = CatalogEntry(self.document, metadata, revision + 1, datetime.now(UTC))
        return self.entry

    def get(self, document_id):
        if not self.entry or document_id != self.document.id:
            raise CatalogEntryNotFoundError("Trabalho não encontrado no acervo.")
        return self.entry

    def list_entries(self, filters, limit, offset):
        return CatalogPage(
            (self.entry,) if self.entry and offset == 0 else (), int(bool(self.entry))
        )

    def search(self, query, filters, limit, offset):
        self.last_search = (query, filters, limit, offset)
        hits = (
            ()
            if offset
            else (CatalogMatch(self.entry, f"{'a' * 64}:page:2", 2, "Metodologia " * 100, 0.5),)
        )
        return CatalogMatches(hits, 1, 1)

    def get_evidence(self, document_id, unit_id):
        entry = self.get(document_id)
        if unit_id != f"{'a' * 64}:page:2":
            raise CatalogEntryNotFoundError("Evidência não encontrada neste trabalho.")
        return CatalogEvidence(entry, unit_id, 2, "Texto integral da página dois.")


@pytest.fixture
def catalog_client():
    repository = FixtureCatalogRepository()
    app.dependency_overrides[get_catalog_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            yield client, repository
    finally:
        app.dependency_overrides.clear()


def test_catalog_metadata_reopens_and_preserves_concurrent_edit(catalog_client):
    client, repository = catalog_client
    path = f"/api/v1/catalog/documents/{repository.document.id}"
    assert client.get(path).status_code == 404
    created = client.put(
        path,
        json={
            "metadata": {"title": "  Pesquisa verificável  ", "area": "   ", "author": "Ana"},
            "expected_revision": 0,
        },
    )
    assert created.status_code == 200
    entry = created.json()
    assert entry["metadata"]["title"] == "Pesquisa verificável"
    assert entry["metadata"]["area"] is None
    assert entry["metadata_source"] == "manual"
    assert entry["metadata_revision"] == 1
    assert entry["document"]["sha256"] == repository.document.sha256
    assert client.get(path).json() == entry
    assert client.get("/api/v1/catalog/documents").json()["total"] == 1

    updated = client.put(
        path, json={"metadata": {"title": "Título revisado"}, "expected_revision": 1}
    )
    assert updated.json()["metadata_revision"] == 2
    conflict = client.put(
        path, json={"metadata": {"title": "Edição antiga"}, "expected_revision": 1}
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "catalog_revision_conflict"
    assert client.get(path).json() == updated.json()
    assert (
        client.put(
            path,
            json={
                "metadata": {"title": "Cadastro duplicado"},
                "expected_revision": 0,
            },
        ).status_code
        == 409
    )


def test_catalog_search_forwards_filters_and_opens_only_the_requested_source(catalog_client):
    client, repository = catalog_client
    repository.save(repository.document.id, AcademicMetadata("Trabalho"), 0)
    response = client.post(
        "/api/v1/catalog/search",
        json={
            "query": "  metodologia  ",
            "filters": {"year_from": 2024, "advisor": "  Joana  "},
            "limit": 1,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["query"] == "metodologia"
    assert result["retrieval_mode"] == "lexical"
    assert result["total_hits"] == result["total_documents"] == 1
    assert result["filters"]["advisor"] == "Joana"
    assert repository.last_search[1].year_from == 2024
    hit = result["hits"][0]
    assert len(hit["snippet"]) <= 320
    assert hit["entry"]["document"]["id"] == str(repository.document.id)
    evidence = client.get(
        f"/api/v1/catalog/documents/{repository.document.id}/evidence/{hit['unit_id']}"
    )
    assert evidence.json()["text"] == "Texto integral da página dois."
    assert evidence.json()["page"] == 2
    assert (
        client.get(f"/api/v1/catalog/documents/{uuid4()}/evidence/{hit['unit_id']}").status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/catalog/documents/{repository.document.id}/evidence/unknown"
        ).status_code
        == 404
    )
    later = client.post("/api/v1/catalog/search", json={"query": "metodologia", "offset": 99})
    assert later.json()["hits"] == []
    assert later.json()["total_hits"] == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"query": "   "},
        {"query": "a" * 201},
        {"query": "abc", "limit": 51},
        {"query": "abc", "offset": -1},
        {"query": "abc", "filters": {"unknown": "yes"}},
        {"query": "abc", "filters": {"year_from": 2025, "year_to": 2024}},
        {"query": "abc", "retrieval_mode": "vector"},
    ],
)
def test_catalog_rejects_invalid_search(catalog_client, payload):
    client, _ = catalog_client
    assert client.post("/api/v1/catalog/search", json=payload).status_code == 422


@pytest.mark.parametrize(
    "metadata",
    [
        {"title": " "},
        {"title": "x", "publication_year": 1599},
        {"title": "x", "document_type": "invented"},
        {"title": "x", "title_source": "llm"},
        {"title": "x", "source_url": "javascript:alert(1)"},
        {"title": "x", "source_url": "https://user:secret@example.org/work"},
    ],
)
def test_catalog_rejects_invalid_metadata(catalog_client, metadata):
    client, repository = catalog_client
    assert (
        client.put(
            f"/api/v1/catalog/documents/{repository.document.id}",
            json={
                "metadata": metadata,
                "expected_revision": 0,
            },
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "query",
    [
        "limit=101",
        "offset=-1",
        "year_from=2025&year_to=2024",
        "unknown=yes",
    ],
)
def test_catalog_rejects_invalid_list_filters(catalog_client, query):
    client, _ = catalog_client
    assert client.get(f"/api/v1/catalog/documents?{query}").status_code == 422


def test_catalog_database_errors_are_explicit(catalog_client, monkeypatch):
    client, repository = catalog_client

    def fail(*args):
        raise DocumentRepositoryError("Banco indisponível.")

    monkeypatch.setattr(repository, "get", fail)
    response = client.get(f"/api/v1/catalog/documents/{repository.document.id}")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_unavailable"
    app.dependency_overrides.pop(get_catalog_repository)
    app.dependency_overrides[get_settings] = lambda: Settings(database_url=None)
    assert client.get("/api/v1/catalog/documents").status_code == 503


def test_catalog_cors_accepts_metadata_updates(catalog_client):
    client, _ = catalog_client
    response = client.options(
        "/api/v1/catalog/documents",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PUT",
        },
    )
    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]
