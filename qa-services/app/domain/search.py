from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LexicalMatch:
    unit_id: str
    document_id: UUID
    page: int
    text: str
    score: float


@dataclass(frozen=True, slots=True)
class EmbeddingProfile:
    model: str
    dimension: int
    chunk_version: str
    max_tokens: int
    overlap_tokens: int


@dataclass(frozen=True, slots=True)
class EmbeddedChunk:
    unit_id: str
    page: int
    chunk_index: int
    text: str
    embedding: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class VectorMatch:
    unit_id: str
    document_id: UUID
    page: int
    chunk_index: int
    text: str
    score: float


@dataclass(frozen=True, slots=True)
class SearchHit:
    unit_id: str
    page: int
    snippet: str
    score: float


@dataclass(frozen=True, slots=True)
class SearchResult:
    document_id: UUID
    query: str
    hits: tuple[SearchHit, ...]
    retrieval_mode: str
    embedding_profile: EmbeddingProfile | None = None
