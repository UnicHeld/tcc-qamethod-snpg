from pathlib import Path
from typing import Protocol

from app.domain.evaluation import DocumentRevision
from app.domain.documents import StoredDocument, StoredDocumentPage, StoredDocumentUnit
from app.services.parser_service import ParsedDocument, ParserService


class DocumentNotFoundError(Exception):
    pass


class DocumentRepositoryError(Exception):
    pass


class DocumentRepository(Protocol):
    def save(self, file_name: str, document: ParsedDocument) -> StoredDocument: ...

    def list_documents(self) -> tuple[StoredDocument, ...]: ...

    def get(self, document_id: str) -> StoredDocument: ...

    def list_units(self, document_id: str) -> tuple[StoredDocumentUnit, ...]: ...

    def list_pages(self, document_id: str) -> tuple[StoredDocumentPage, ...]: ...

    def get_revision(self, document_id: str) -> DocumentRevision: ...


class DocumentService:
    def __init__(self, repository: DocumentRepository, max_pages: int) -> None:
        self.repository = repository
        self.parser = ParserService(max_pages=max_pages)

    def admit(self, file_name: str | None, pdf_content: bytes) -> StoredDocument:
        safe_file_name = Path(file_name or "documento.pdf").name
        parsed = self.parser.extract_text(pdf_content)
        return self.repository.save(safe_file_name, parsed)
