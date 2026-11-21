from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.domain.documents import StoredDocument

DocumentType = Literal["thesis", "dissertation", "other"]


@dataclass(frozen=True, slots=True)
class AcademicMetadata:
    title: str
    document_type: DocumentType | None = None
    publication_year: int | None = None
    area: str | None = None
    institution: str | None = None
    program: str | None = None
    author: str | None = None
    advisor: str | None = None
    coadvisor: str | None = None
    source_url: str | None = None


@dataclass(frozen=True, slots=True)
class CatalogFilters:
    document_type: DocumentType | None = None
    year_from: int | None = None
    year_to: int | None = None
    area: str | None = None
    institution: str | None = None
    program: str | None = None
    author: str | None = None
    advisor: str | None = None
    coadvisor: str | None = None


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    document: StoredDocument
    metadata: AcademicMetadata
    metadata_revision: int
    updated_at: datetime
    metadata_source: Literal["manual"] = "manual"


@dataclass(frozen=True, slots=True)
class CatalogPage:
    entries: tuple[CatalogEntry, ...]
    total: int


@dataclass(frozen=True, slots=True)
class CatalogMatch:
    entry: CatalogEntry
    unit_id: str
    page: int
    text: str
    score: float


@dataclass(frozen=True, slots=True)
class CatalogMatches:
    hits: tuple[CatalogMatch, ...]
    total_hits: int
    total_documents: int


@dataclass(frozen=True, slots=True)
class CatalogEvidence:
    entry: CatalogEntry
    unit_id: str
    page: int
    text: str
