from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from app.domain.catalog import DocumentType
from app.schemas.documents import DocumentResponse


def blank_to_none(value: object) -> object:
    return None if isinstance(value, str) and not value.strip() else value


OptionalText = Annotated[str | None, Field(max_length=300), BeforeValidator(blank_to_none)]
Year = Annotated[int, Field(ge=1600, le=2100)]


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class AcademicMetadataRequest(CatalogModel):
    title: str = Field(min_length=1, max_length=500)
    document_type: DocumentType | None = None
    publication_year: Year | None = None
    area: OptionalText = None
    institution: OptionalText = None
    program: OptionalText = None
    author: OptionalText = None
    advisor: OptionalText = None
    coadvisor: OptionalText = None
    source_url: Annotated[str | None, Field(max_length=2000), BeforeValidator(blank_to_none)] = None

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is not None:
            url = HttpUrl(value)
            if url.username is not None or url.password is not None:
                raise ValueError("A URL de origem não pode conter credenciais.")
        return value


class SaveCatalogEntryRequest(CatalogModel):
    metadata: AcademicMetadataRequest
    expected_revision: int = Field(ge=0)


class CatalogFiltersRequest(CatalogModel):
    document_type: DocumentType | None = None
    year_from: Year | None = None
    year_to: Year | None = None
    area: OptionalText = None
    institution: OptionalText = None
    program: OptionalText = None
    author: OptionalText = None
    advisor: OptionalText = None
    coadvisor: OptionalText = None

    @model_validator(mode="after")
    def validate_year_range(self) -> Self:
        if (
            self.year_from is not None
            and self.year_to is not None
            and self.year_from > self.year_to
        ):
            raise ValueError("O ano inicial não pode ser maior que o ano final.")
        return self


class CatalogListRequest(CatalogFiltersRequest):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1_000_000)


class CatalogEntryResponse(CatalogModel):
    document: DocumentResponse
    metadata: AcademicMetadataRequest
    metadata_revision: int = Field(ge=1)
    metadata_source: Literal["manual"]
    updated_at: datetime


class CatalogListResponse(CatalogModel):
    entries: tuple[CatalogEntryResponse, ...]
    total: int = Field(ge=0)
    limit: int
    offset: int


class CatalogSearchRequest(CatalogModel):
    query: str = Field(min_length=1, max_length=200)
    filters: CatalogFiltersRequest = Field(default_factory=CatalogFiltersRequest)
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=1_000_000)


class CatalogHitResponse(CatalogModel):
    entry: CatalogEntryResponse
    unit_id: str
    page: int = Field(ge=1)
    snippet: str
    score: float


class CatalogSearchResponse(CatalogModel):
    query: str
    filters: CatalogFiltersRequest
    retrieval_mode: Literal["lexical"] = "lexical"
    hits: tuple[CatalogHitResponse, ...]
    total_hits: int = Field(ge=0)
    total_documents: int = Field(ge=0)
    limit: int
    offset: int


class CatalogEvidenceResponse(CatalogModel):
    entry: CatalogEntryResponse
    unit_id: str
    page: int = Field(ge=1)
    text: str
