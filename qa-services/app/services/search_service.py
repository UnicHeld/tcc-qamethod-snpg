from typing import Protocol
from uuid import UUID

from app.domain.search import LexicalMatch, LexicalSearchResult, SearchHit


class InvalidSearchQueryError(Exception):
    pass


class SearchRepository(Protocol):
    def search_lexical(
        self, document_id: str, query: str, limit: int
    ) -> tuple[LexicalMatch, ...]: ...


class SearchService:
    MAX_QUERY_CHARACTERS = 200
    MAX_SNIPPET_CHARACTERS = 320

    def __init__(self, repository: SearchRepository) -> None:
        self.repository = repository

    def search(self, document_id: str, query: str, limit: int) -> LexicalSearchResult:
        normalized_query = query.strip()
        if not normalized_query:
            raise InvalidSearchQueryError("Informe uma consulta não vazia.")
        if len(normalized_query) > self.MAX_QUERY_CHARACTERS:
            raise InvalidSearchQueryError(
                f"A consulta deve ter no máximo {self.MAX_QUERY_CHARACTERS} caracteres."
            )

        matches = self.repository.search_lexical(
            document_id, normalized_query, limit
        )
        return LexicalSearchResult(
            document_id=matches[0].document_id if matches else self._document_id(document_id),
            query=normalized_query,
            hits=tuple(
                SearchHit(
                    unit_id=match.unit_id,
                    page=match.page,
                    snippet=self._snippet(match.text, normalized_query),
                    score=match.score,
                )
                for match in matches
            ),
        )

    @staticmethod
    def _document_id(document_id: str) -> UUID:
        return UUID(document_id)

    @classmethod
    def _snippet(cls, text: str, query: str) -> str:
        if len(text) <= cls.MAX_SNIPPET_CHARACTERS:
            return text

        folded_text = text.casefold()
        positions = [
            folded_text.find(term.casefold())
            for term in query.split()
            if term and folded_text.find(term.casefold()) >= 0
        ]
        match_position = min(positions, default=0)
        radius = cls.MAX_SNIPPET_CHARACTERS // 2
        start = max(0, match_position - radius)
        end = min(len(text), start + cls.MAX_SNIPPET_CHARACTERS)
        start = max(0, end - cls.MAX_SNIPPET_CHARACTERS)
        snippet = text[start:end]
        if start:
            snippet = "…" + snippet[1:]
        if end < len(text):
            snippet = snippet[:-1] + "…"
        return snippet
