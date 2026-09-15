from uuid import uuid4

import pytest

from app.domain.search import LexicalMatch
from app.services.search_service import InvalidSearchQueryError, SearchService


class StubSearchRepository:
    def __init__(self, matches: tuple[LexicalMatch, ...] = ()) -> None:
        self.matches = matches
        self.calls: list[tuple[str, str, int]] = []

    def search_lexical(self, document_id, query, limit):
        self.calls.append((document_id, query, limit))
        return self.matches


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
