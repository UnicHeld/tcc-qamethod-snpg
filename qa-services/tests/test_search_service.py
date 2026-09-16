from uuid import UUID, uuid4

import pytest

from app.domain.documents import StoredDocumentUnit
from app.domain.search import EmbeddingProfile, LexicalMatch, VectorMatch
from app.services.document_service import DocumentNotFoundError, DocumentRepositoryError
from app.services.search_service import InvalidSearchQueryError, SearchService


class StubSearchRepository:
    def __init__(self, matches: tuple[LexicalMatch, ...] = ()) -> None:
        self.matches = matches
        self.calls: list[tuple[str, str, int]] = []
        self.vector_indexed = False
        self.saved_chunks = ()

    def search_lexical(self, document_id, query, limit):
        self.calls.append((document_id, query, limit))
        return self.matches

    def list_units(self, document_id):
        return (
            StoredDocumentUnit(
                id="unit-1",
                document_id=uuid4(),
                page=2,
                text="Método de análise qualitativa.",
            ),
        )

    def is_vector_indexed(self, document_id, profile):
        return self.vector_indexed

    def replace_vector_index(self, document_id, profile, chunks):
        self.saved_chunks = chunks
        self.vector_indexed = True

    def search_vector(self, document_id, profile, query_embedding, limit):
        return (
            VectorMatch(
                unit_id="unit-1",
                document_id=UUID(document_id),
                page=2,
                chunk_index=0,
                text="Método de análise qualitativa.",
                score=0.82,
            ),
        )[:limit]


class StubEmbedder:
    profile = EmbeddingProfile(
        model="test/model",
        dimension=3,
        chunk_version="test-v1",
        max_tokens=4,
        overlap_tokens=1,
    )

    def chunk(self, text):
        return (text,)

    def embed_passages(self, passages):
        return tuple((0.1, 0.2, 0.3) for _ in passages)

    def embed_query(self, query):
        return (0.3, 0.2, 0.1)


def test_search_normalizes_query_and_limits_plain_text_snippet() -> None:
    document_id = uuid4()
    long_text = "prefixo " * 50 + "metodologia verificável " + "sufixo " * 50
    repository = StubSearchRepository(
        (
            LexicalMatch(
                unit_id="unit-1",
                document_id=document_id,
                page=4,
                text=long_text,
                score=0.75,
            ),
        )
    )

    result = SearchService(repository).search(
        str(document_id), "  metodologia verificável  ", 5
    )

    assert repository.calls == [(str(document_id), "metodologia verificável", 5)]
    assert result.document_id == document_id
    assert result.query == "metodologia verificável"
    assert len(result.hits[0].snippet) == SearchService.MAX_SNIPPET_CHARACTERS
    assert "metodologia verificável" in result.hits[0].snippet
    assert result.hits[0].snippet.startswith("…")
    assert result.hits[0].snippet.endswith("…")


@pytest.mark.parametrize("query", ["", "   ", "x" * 201])
def test_search_rejects_empty_or_excessive_query(query: str) -> None:
    with pytest.raises(InvalidSearchQueryError):
        SearchService(StubSearchRepository()).search(str(uuid4()), query, 10)


def test_vector_search_indexes_units_and_returns_profile_metadata() -> None:
    repository = StubSearchRepository()
    document_id = uuid4()

    result = SearchService(repository, StubEmbedder()).search(
        str(document_id), "abordagem interpretativa", 5, "vector"
    )

    assert repository.vector_indexed is True
    assert repository.saved_chunks[0].unit_id == "unit-1"
    assert repository.saved_chunks[0].embedding == (0.1, 0.2, 0.3)
    assert result.retrieval_mode == "vector"
    assert result.embedding_profile == StubEmbedder.profile
    assert result.hits[0].score == 0.82


def test_vector_search_reuses_existing_index() -> None:
    repository = StubSearchRepository()
    repository.vector_indexed = True

    SearchService(repository, StubEmbedder()).search(
        str(uuid4()), "abordagem interpretativa", 5, "vector"
    )

    assert repository.saved_chunks == ()


@pytest.mark.parametrize(
    "repository_error",
    [
        DocumentNotFoundError("Documento não encontrado."),
        DocumentRepositoryError("O banco não está disponível."),
    ],
)
def test_vector_search_preserves_document_repository_errors(repository_error) -> None:
    class FailingRepository(StubSearchRepository):
        def is_vector_indexed(self, document_id, profile):
            raise repository_error

    with pytest.raises(type(repository_error), match=str(repository_error)):
        SearchService(FailingRepository(), StubEmbedder()).search(
            str(uuid4()), "abordagem interpretativa", 5, "vector"
        )
