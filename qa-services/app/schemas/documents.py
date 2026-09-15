from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.documents import PageExtractionStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    sha256: str
    page_count: int = Field(ge=1)
    character_count: int = Field(ge=1)
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: tuple[DocumentResponse, ...]


class DocumentUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: UUID
    page: int = Field(ge=1)
    text: str = Field(min_length=1)


class DocumentUnitsResponse(BaseModel):
    units: tuple[DocumentUnitResponse, ...]


class DocumentPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    page: int = Field(ge=1)
    status: PageExtractionStatus
    character_count: int = Field(ge=0)
    has_images: bool


class DocumentPagesResponse(BaseModel):
    pages: tuple[DocumentPageResponse, ...]
