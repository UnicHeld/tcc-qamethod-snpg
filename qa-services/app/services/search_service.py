from typing import Literal, Protocol
from uuid import UUID

from app.domain.documents import StoredDocumentUnit
from app.domain.search import (
    EmbeddedChunk,
    EmbeddingProfile,
    LexicalMatch,
    SearchHit,
    SearchResult,
    VectorMatch,
)
from app.services.document_service import DocumentNotFoundError, DocumentRepositoryError


class InvalidSearchQueryError(Exception):
    pass


class VectorSearchUnavailableError(Exception):
    pass


class TextEmbedder(Protocol):
    profile: EmbeddingProfile

    def chunk(self, text: str) -> tuple[str, ...]: ...

    def embed_passages(self, passages: tuple[str, ...]) -> tuple[tuple[float, ...], ...]: ...

    def embed_query(self, query: str) -> tuple[float, ...]: ...


class SearchRepository(Protocol):
    def search_lexical(
        self, document_id: str, query: str, limit: int
    ) -> tuple[LexicalMatch, ...]: ...

    def list_units(self, document_id: str) -> tuple[StoredDocumentUnit, ...]: ...

    def is_vector_indexed(self, document_id: str, profile: EmbeddingProfile) -> bool: ...

    def replace_vector_index(
        self,
        document_id: str,
        profile: EmbeddingProfile,
        chunks: tuple[EmbeddedChunk, ...],
    ) -> None: ...

    def search_vector(
        self,
        document_id: str,
        profile: EmbeddingProfile,
        query_embedding: tuple[float, ...],
        limit: int,
    ) -> tuple[VectorMatch, ...]: ...


class SearchService:
    MAX_QUERY_CHARACTERS = 200
    MAX_SNIPPET_CHARACTERS = 320

    def __init__(
        self, repository: SearchRepository, embedder: TextEmbedder | None = None
    ) -> None:
        self.repository = repository
        self.embedder = embedder

    def search(
        self,
        document_id: str,
        query: str,
        limit: int,
        retrieval_mode: Literal["lexical", "vector"] = "lexical",
    ) -> SearchResult:
        normalized_query = query.strip()
        if not normalized_query:
            raise InvalidSearchQueryError("Informe uma consulta não vazia.")
        if len(normalized_query) > self.MAX_QUERY_CHARACTERS:
            raise InvalidSearchQueryError(
                f"A consulta deve ter no máximo {self.MAX_QUERY_CHARACTERS} caracteres."
            )

        if retrieval_mode == "vector":
            return self._search_vector(document_id, normalized_query, limit)

        matches = self.repository.search_lexical(document_id, normalized_query, limit)
        return SearchResult(
            document_id=matches[0].document_id if matches else self._document_id(document_id),
            query=normalized_query,
            retrieval_mode="lexical",
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

    def _search_vector(self, document_id: str, query: str, limit: int) -> SearchResult:
        if self.embedder is None:
            raise VectorSearchUnavailableError("A busca vetorial não está habilitada.")

        profile = self.embedder.profile
        try:
            if not self.repository.is_vector_indexed(document_id, profile):
                chunks = self._embed_document(document_id)
                self.repository.replace_vector_index(document_id, profile, chunks)
            query_embedding = self.embedder.embed_query(query)
        except (
            DocumentNotFoundError,
            DocumentRepositoryError,
            VectorSearchUnavailableError,
        ):
            raise
        except Exception as error:
            raise VectorSearchUnavailableError(
                "Não foi possível carregar o modelo ou gerar os embeddings locais."
            ) from error

        matches = self.repository.search_vector(
            document_id, profile, query_embedding, limit
        )
        return SearchResult(
            document_id=matches[0].document_id if matches else self._document_id(document_id),
            query=query,
            retrieval_mode="vector",
            embedding_profile=profile,
            hits=tuple(
                SearchHit(
                    unit_id=match.unit_id,
                    page=match.page,
                    snippet=self._snippet(match.text, query),
                    score=match.score,
                )
                for match in matches
            ),
        )

    def _embed_document(self, document_id: str) -> tuple[EmbeddedChunk, ...]:
        if self.embedder is None:
            raise VectorSearchUnavailableError("A busca vetorial não está habilitada.")

        pending: list[tuple[str, int, int, str]] = []
        for unit in self.repository.list_units(document_id):
            for chunk_index, chunk_text in enumerate(self.embedder.chunk(unit.text)):
                pending.append((unit.id, unit.page, chunk_index, chunk_text))
        if not pending:
            raise VectorSearchUnavailableError(
                "O documento não contém texto suficiente para indexação vetorial."
            )

        embeddings = self.embedder.embed_passages(
            tuple(chunk_text for _, _, _, chunk_text in pending)
        )
        if len(embeddings) != len(pending):
            raise VectorSearchUnavailableError(
                "O modelo retornou uma quantidade inesperada de embeddings."
            )
        return tuple(
            EmbeddedChunk(
                unit_id=unit_id,
                page=page,
                chunk_index=chunk_index,
                text=chunk_text,
                embedding=embedding,
            )
            for (unit_id, page, chunk_index, chunk_text), embedding in zip(
                pending, embeddings, strict=True
            )
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
