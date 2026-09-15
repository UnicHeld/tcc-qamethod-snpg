from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.domain.search import LexicalMatch
from app.main import app
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
        "hits": [
            {
                "unit_id": f"{'a' * 64}:page:2",
                "page": 2,
                "snippet": "A metodologia usa uma fixture sintética e verificável.",
                "score": 0.5,
            }
        ],
    }


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
