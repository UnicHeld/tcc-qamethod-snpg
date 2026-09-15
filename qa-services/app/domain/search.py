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
class SearchHit:
    unit_id: str
    page: int
    snippet: str
    score: float


@dataclass(frozen=True, slots=True)
class LexicalSearchResult:
    document_id: UUID
    query: str
    hits: tuple[SearchHit, ...]
