from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: UUID
    query: str = Field(max_length=200)
    limit: int = Field(default=10, ge=1, le=20, strict=True)
    retrieval_mode: Literal["lexical", "vector"] = "lexical"


class SearchHitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit_id: str
    page: int = Field(ge=1)
    snippet: str = Field(min_length=1, max_length=320)
    score: float = Field(ge=0, allow_inf_nan=False)


class SearchResponse(BaseModel):
    document_id: UUID
    query: str
    retrieval_mode: Literal["lexical", "vector"] = "lexical"
    embedding_model: str | None = None
    embedding_dimension: int | None = Field(default=None, gt=0)
    chunk_version: str | None = None
    hits: tuple[SearchHitResponse, ...]
