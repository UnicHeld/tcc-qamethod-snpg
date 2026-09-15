from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.domain.documents import StoredDocument, StoredDocumentPage, StoredDocumentUnit
from app.main import app
from app.routers.documents import get_document_repository
from app.services.document_service import DocumentNotFoundError
from tests.pdf_factory import synthetic_pdf


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents_by_hash: dict[str, StoredDocument] = {}
        self.units_by_document: dict[UUID, tuple[StoredDocumentUnit, ...]] = {}
        self.pages_by_document: dict[UUID, tuple[StoredDocumentPage, ...]] = {}

    def save(self, file_name, document):
        existing = self.documents_by_hash.get(document.sha256)
        if existing:
            return existing
        stored = StoredDocument(
            id=uuid4(),
            file_name=file_name,
            sha256=document.sha256,
            page_count=document.page_count,
            character_count=len(document.text),
            created_at=datetime.now(UTC),
        )
        self.documents_by_hash[document.sha256] = stored
        self.units_by_document[stored.id] = tuple(
            StoredDocumentUnit(
                id=unit.id,
                document_id=stored.id,
                page=unit.page,
                text=unit.text,
            )
            for unit in document.units
        )
        self.pages_by_document[stored.id] = tuple(
            StoredDocumentPage(
                document_id=stored.id,
                page=page.page,
                status=page.status,
                character_count=page.character_count,
                has_images=page.has_images,
            )
            for page in document.pages
        )
        return stored

    def list_documents(self):
        return tuple(self.documents_by_hash.values())

    def get(self, document_id):
        return next(
            (
                document
                for document in self.documents_by_hash.values()
                if str(document.id) == document_id
            ),
            None,
        ) or self._raise_not_found()

    def list_units(self, document_id):
        document = self.get(document_id)
        return self.units_by_document[document.id]

    def list_pages(self, document_id):
        document = self.get(document_id)
        return self.pages_by_document[document.id]

    @staticmethod
    def _raise_not_found():
        raise DocumentNotFoundError("Documento não encontrado.")


def setup_function() -> None:
    app.dependency_overrides.clear()


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_document_endpoints_persist_and_reopen_extracted_units() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[get_document_repository] = lambda: repository
    fixture_text = "Conteudo sintetico autorizado para persistencia."
    payload = synthetic_pdf(fixture_text)

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/documents",
            files={"file": ("fixture.pdf", payload, "application/pdf")},
        )
        duplicate = client.post(
            "/api/v1/documents",
            files={"file": ("outro-nome.pdf", payload, "application/pdf")},
        )
        document_id = created.json()["id"]
        reopened = client.get(f"/api/v1/documents/{document_id}")
        units = client.get(f"/api/v1/documents/{document_id}/units")
        pages = client.get(f"/api/v1/documents/{document_id}/pages")
        listing = client.get("/api/v1/documents")

    assert created.status_code == 201
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == document_id
    assert reopened.json() == created.json()
    assert listing.json()["documents"] == [created.json()]
    assert units.status_code == 200
    assert units.json()["units"][0]["page"] == 1
    assert "Conteudo sintetico" in units.json()["units"][0]["text"]
    assert pages.status_code == 200
    assert pages.json()["pages"] == [
        {
            "document_id": document_id,
            "page": 1,
            "status": "extracted",
            "character_count": len(fixture_text),
            "has_images": False,
        }
    ]


def test_document_endpoint_reports_missing_document() -> None:
    repository = InMemoryDocumentRepository()
    app.dependency_overrides[get_document_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.get(f"/api/v1/documents/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "document_not_found"
