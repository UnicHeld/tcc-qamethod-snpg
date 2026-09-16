import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.domain.evaluation import DocumentRevision, DocumentUnit
from app.domain.insights import InsightDraft
from app.domain.search import SearchHit, SearchResult
from app.schemas.evaluation import EvaluationMode, UsageKind
from app.services.evaluation_service import ProviderError
from app.services.insight_service import (
    DemoInsightAdapter,
    GeminiInsightAdapter,
    InsightGenerationResult,
    InsufficientEvidenceError,
    build_evidence_package,
    create_insight_adapter,
    finalize_insight,
)


def revision() -> DocumentRevision:
    sha256 = "b" * 64
    return DocumentRevision(
        sha256=sha256,
        page_count=2,
        units=(
            DocumentUnit(
                id=f"{sha256}:page:2",
                page=2,
                text="Foram realizadas entrevistas.",
            ),
        ),
    )


def search_result(document_id) -> SearchResult:
    return SearchResult(
        document_id=document_id,
        query="Como os participantes foram ouvidos?",
        retrieval_mode="lexical",
        hits=(
            SearchHit(
                unit_id=f"{'b' * 64}:page:2",
                page=2,
                snippet="Foram realizadas entrevistas.",
                score=0.8,
            ),
        ),
    )


def test_demo_insight_uses_and_validates_frozen_evidence() -> None:
    document_id = uuid4()
    package = build_evidence_package(document_id, revision(), search_result(document_id))
    adapter = DemoInsightAdapter()

    generation = asyncio.run(adapter.generate(package))
    execution = finalize_insight(package, adapter, generation)

    assert execution.report.simulated is True
    assert execution.report.citation_ids == ("E1",)
    assert execution.evidence_package.items[0].page == 2
    assert "Simulado" in execution.markdown


def test_package_requires_at_least_one_retrieved_evidence() -> None:
    document_id = uuid4()
    result = SearchResult(
        document_id=document_id,
        query="Pergunta sem resultado",
        retrieval_mode="lexical",
        hits=(),
    )

    with pytest.raises(InsufficientEvidenceError):
        build_evidence_package(document_id, revision(), result)


def test_finalize_rejects_citation_not_in_package() -> None:
    document_id = uuid4()
    package = build_evidence_package(document_id, revision(), search_result(document_id))
    adapter = DemoInsightAdapter()
    invalid = InsightGenerationResult(
        draft=InsightDraft(answer="Resposta inválida", citation_ids=("E99",)),
        usage_kind=UsageKind.SIMULATED,
    )

    with pytest.raises(ProviderError, match="estruturado inválido"):
        finalize_insight(package, adapter, invalid)


def test_real_insight_requires_provider_configuration() -> None:
    with pytest.raises(ProviderError):
        create_insight_adapter(mode=EvaluationMode.REAL, settings=Settings())


def test_gemini_insight_requests_structured_answer_from_frozen_package() -> None:
    document_id = uuid4()
    package = build_evidence_package(document_id, revision(), search_result(document_id))
    draft = InsightDraft(
        answer="Os participantes foram ouvidos por entrevistas.",
        citation_ids=("E1",),
    )

    class FakeModels:
        def __init__(self) -> None:
            self.arguments: dict[str, object] = {}

        def generate_content(self, **kwargs: object) -> object:
            self.arguments = kwargs
            return SimpleNamespace(
                text=draft.model_dump_json(),
                usage_metadata=SimpleNamespace(
                    prompt_token_count=25,
                    candidates_token_count=12,
                ),
            )

    models = FakeModels()
    adapter = GeminiInsightAdapter(
        api_key="test-key",
        model="test-model",
        client_factory=lambda api_key: SimpleNamespace(models=models),
    )

    generation = asyncio.run(adapter.generate(package))
    execution = finalize_insight(package, adapter, generation)

    assert generation.usage_kind is UsageKind.ACTUAL
    assert generation.input_tokens == 25
    assert generation.output_tokens == 12
    assert execution.report.simulated is False
    assert execution.report.citation_ids == ("E1",)
    assert package.items[0].text in str(models.arguments["contents"])
    config = models.arguments["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema
