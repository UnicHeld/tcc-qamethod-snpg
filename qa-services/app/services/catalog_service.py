from typing import Protocol
from uuid import UUID

from app.domain.catalog import (
    AcademicMetadata,
    CatalogEntry,
    CatalogEvidence,
    CatalogFilters,
    CatalogMatches,
    CatalogPage,
)


class CatalogEntryNotFoundError(Exception):
    pass


class CatalogRevisionConflictError(Exception):
    pass


class CatalogRepository(Protocol):
    def save(
        self, document_id: UUID, metadata: AcademicMetadata, expected_revision: int
    ) -> CatalogEntry: ...

    def get(self, document_id: UUID) -> CatalogEntry: ...

    def list_entries(self, filters: CatalogFilters, limit: int, offset: int) -> CatalogPage: ...

    def search(
        self, query: str, filters: CatalogFilters, limit: int, offset: int
    ) -> CatalogMatches: ...

    def get_evidence(self, document_id: UUID, unit_id: str) -> CatalogEvidence: ...
