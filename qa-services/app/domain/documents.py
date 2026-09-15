from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class PageExtractionStatus(StrEnum):
    EXTRACTED = "extracted"
    OCR_CANDIDATE = "ocr_candidate"
    NO_TEXT = "no_text"


@dataclass(frozen=True, slots=True)
class StoredDocument:
    id: UUID
    file_name: str
    sha256: str
    page_count: int
    character_count: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredDocumentUnit:
    id: str
    document_id: UUID
    page: int
    text: str


@dataclass(frozen=True, slots=True)
class StoredDocumentPage:
    document_id: UUID
    page: int
    status: PageExtractionStatus
    character_count: int
    has_images: bool
