from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.domain.search import EmbeddingProfile, LexicalMatch, VectorMatch
from app.main import app
from app.routers import search as search_router
from app.routers.search import get_search_repository
from app.services.document_service import DocumentNotFoundError, DocumentRepositoryError


class InMemorySearchRepository:
    def __init__(self, document_id: UUID) -> None:
        self.document_id = document_id

    def search_lexical(self, document_id, query, limit):
        if document_id != str(self.document_id):
            raise DocumentNotFoundError("Documento não encontrado.")
        if query == "sem resultado":
            return ()
        return (
            LexicalMatch(
                unit_id=f"{'a' * 64}:page:2",
                document_id=self.document_id,
                page=2,
                text="A metodologia usa uma fixture sintética e verificável.",
                score=0.5,
            ),
        )[:limit]

    def is_vector_indexed(self, document_id, profile):
        if document_id != str(self.document_id):
            raise DocumentNotFoundError("Documento não encontrado.")
        return True

    def search_vector(self, document_id, profile, query_embedding, limit):
        return (
            VectorMatch(
                unit_id=f"{'a' * 64}:page:2",
                document_id=self.document_id,
                page=2,
                chunk_index=0,
                text="Abordagem qualitativa aplicada à avaliação.",
                score=0.91,
            ),
        )[:limit]


class UnavailableSearchRepository:
    def search_lexical(self, document_id, query, limit):
        raise DocumentRepositoryError("A busca no banco falhou.")


def setup_function() -> None:
    app.dependency_overrides.clear()


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_search_endpoint_returns_lexical_evidence() -> None:
    document_id = uuid4()
    app.dependency_overrides[get_search_repository] = lambda: InMemorySearchRepository(
        document_id
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/search",
            json={
                "document_id": str(document_id),
                "query": "  metodologia  ",
                "limit": 5,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "document_id": str(document_id),
        "query": "metodologia",
        "retrieval_mode": "lexical",
        "embedding_model": None,
        "embedding_dimension": None,
        "chunk_version": None,
        "hits": [
            {
                "unit_id": f"{'a' * 64}:page:2",
                "page": 2,
                "snippet": "A metodologia usa uma fixture sintética e verificável.",
                "score": 0.5,
            }
        ],
    }


def test_search_endpoint_returns_vector_evidence(monkeypatch) -> None:
    class StubEmbedder:
        profile = EmbeddingProfile(
            model="test/multilingual",
            dimension=3,
            chunk_version="test-v1",
            max_tokens=4,
            overlap_tokens=1,
        )

        def embed_query(self, query):
            return (0.1, 0.2, 0.3)

    document_id = uuid4()
    app.dependency_overrides[get_search_repository] = lambda: InMemorySearchRepository(
        document_id
    )
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="postgresql://unused",
        vector_search_enabled=True,
    )
    monkeypatch.setattr(
        search_router, "_get_vector_embedder", lambda profile, cache: StubEmbedder()
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/search",
            json={
                "document_id": str(document_id),
                "query": "pesquisa interpretativa",
                "retrieval_mode": "vector",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["retrieval_mode"] == "vector"
    assert payload["embedding_model"] == "test/multilingual"
    assert payload["embedding_dimension"] == 3
    assert payload["chunk_version"] == "test-v1"
    assert payload["hits"][0]["page"] == 2


def test_search_endpoint_rejects_disabled_vector_mode() -> None:
    document_id = uuid4()
    app.dependency_overrides[get_search_repository] = lambda: InMemorySearchRepository(
        document_id
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/search",
            json={
                "document_id": str(document_id),
                "query": "metodologia",
                "retrieval_mode": "vector",
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "vector_search_unavailable"


def test_search_endpoint_returns_empty_hits_without_inventing_evidence() -> None:
    document_id = uuid4()
    app.dependency_overrides[get_search_repository] = lambda: InMemorySearchRepository(
        document_id
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/search",
            json={"document_id": str(document_id), "query": "sem resultado"},
        )

    assert response.status_code == 200
    assert response.json()["hits"] == []


def test_search_endpoint_reports_invalid_query_and_missing_document() -> None:
    document_id = uuid4()
    app.dependency_overrides[get_search_repository] = lambda: InMemorySearchRepository(
        document_id
    )

    with TestClient(app) as client:
        invalid = client.post(
            "/api/v1/search",
            json={"document_id": str(document_id), "query": "   "},
        )
        missing = client.post(
            "/api/v1/search",
            json={"document_id": str(uuid4()), "query": "metodologia"},
        )

    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "invalid_search_query"
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "document_not_found"


def test_search_endpoint_reports_database_unavailable() -> None:
    app.dependency_overrides[get_search_repository] = UnavailableSearchRepository

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/search",
            json={"document_id": str(uuid4()), "query": "metodologia"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "database_unavailable",
        "message": "A busca no banco falhou.",
    }
