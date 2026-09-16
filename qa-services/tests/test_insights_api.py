from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.domain.insights import (
    EvidenceItem,
    EvidencePackage,
    InsightReport,
    StoredInsightRun,
)
from app.domain.runs import RunStatus
from app.main import app
from app.routers.insights import get_insight_repository
from app.services.insight_run_service import (
    InsightRunConflictError,
    InsightRunNotFoundError,
)


class InMemoryInsightRepository:
    def __init__(self) -> None:
        self.insights: dict[UUID, StoredInsightRun] = {}
        self.by_key: dict[str, StoredInsightRun] = {}

    def enqueue(
        self,
        document_id,
        question,
        retrieval_mode,
        retrieval_limit,
        mode,
        provider,
        model,
        prompt_version,
        idempotency_key,
    ):
        if idempotency_key in self.by_key:
            existing = self.by_key[idempotency_key]
            expected = (
                UUID(document_id),
                question,
                retrieval_mode,
                retrieval_limit,
                mode.value,
            )
            observed = (
                existing.document_id,
                existing.question,
                existing.retrieval_mode,
                existing.retrieval_limit,
                existing.mode,
            )
            if observed != expected:
                raise InsightRunConflictError(
                    "Idempotency-Key já foi usada com outra solicitação."
                )
            return existing
        insight = StoredInsightRun(
            id=uuid4(),
            document_id=UUID(document_id),
            question=question,
            retrieval_mode=retrieval_mode,
            retrieval_limit=retrieval_limit,
            mode=mode.value,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            status=RunStatus.QUEUED,
            usage_kind=None,
            credential_slot=None,
            input_tokens=None,
            output_tokens=None,
            evidence_package=None,
            report=None,
            result_markdown=None,
            error_code=None,
            error_message=None,
            created_at=datetime.now(UTC),
            started_at=None,
            finished_at=None,
        )
        self.insights[insight.id] = insight
        if idempotency_key:
            self.by_key[idempotency_key] = insight
        return insight

    def get(self, insight_id):
        try:
            return self.insights[UUID(insight_id)]
        except (KeyError, ValueError) as error:
            raise InsightRunNotFoundError("Insight não encontrado.") from error

    def list_insights(self, document_id=None):
        insights = tuple(reversed(tuple(self.insights.values())))
        if document_id is None:
            return insights
        return tuple(item for item in insights if item.document_id == UUID(document_id))


def setup_function() -> None:
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def teardown_function() -> None:
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def test_insight_endpoints_are_idempotent_and_publish_only_valid_result() -> None:
    repository = InMemoryInsightRepository()
    app.dependency_overrides[get_insight_repository] = lambda: repository
    document_id = uuid4()
    request = {
        "document_id": str(document_id),
        "question": "Qual metodologia foi utilizada?",
        "retrieval_mode": "lexical",
        "retrieval_limit": 5,
        "mode": "demo",
    }

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/insights",
            json=request,
            headers={"Idempotency-Key": "insight-1"},
        )
        duplicate = client.post(
            "/api/v1/insights",
            json=request,
            headers={"Idempotency-Key": "insight-1"},
        )
        insight_id = created.json()["id"]
        pending = client.get(f"/api/v1/insights/{insight_id}/result")

        package = EvidencePackage(
            document_id=document_id,
            revision_sha256="c" * 64,
            question=request["question"],
            retrieval_mode="lexical",
            items=(
                EvidenceItem(
                    id="E1",
                    unit_id=f"{'c' * 64}:page:1",
                    page=1,
                    text="A pesquisa usou entrevistas.",
                    score=0.8,
                ),
            ),
        )
        report = InsightReport(
            revision_sha256=package.revision_sha256,
            simulated=True,
            question=package.question,
            answer="Resposta simulada.",
            citation_ids=("E1",),
        )
        repository.insights[UUID(insight_id)] = replace(
            repository.insights[UUID(insight_id)],
            status=RunStatus.SUCCEEDED,
            usage_kind="simulated",
            evidence_package=package.model_dump(mode="json"),
            report=report.model_dump(mode="json"),
            result_markdown="# Insight RAG\n",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        result = client.get(f"/api/v1/insights/{insight_id}/result")
        listed = client.get("/api/v1/insights", params={"document_id": str(document_id)})

    assert created.status_code == 202
    assert duplicate.json()["id"] == insight_id
    assert pending.status_code == 409
    assert result.status_code == 200
    assert result.json()["report"]["citation_ids"] == ["E1"]
    assert result.json()["evidence_package"]["items"][0]["page"] == 1
    assert [item["id"] for item in listed.json()["insights"]] == [insight_id]


def test_insight_rejects_key_reuse_and_real_mode_without_confirmation() -> None:
    repository = InMemoryInsightRepository()
    app.dependency_overrides[get_insight_repository] = lambda: repository
    document_id = uuid4()

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/insights",
            json={"document_id": str(document_id), "question": "Primeira pergunta"},
            headers={"Idempotency-Key": "same-key"},
        )
        conflict = client.post(
            "/api/v1/insights",
            json={"document_id": str(document_id), "question": "Outra pergunta"},
            headers={"Idempotency-Key": "same-key"},
        )
        real = client.post(
            "/api/v1/insights",
            json={
                "document_id": str(document_id),
                "question": "Pergunta real",
                "mode": "real",
                "confirm_external_processing": False,
            },
        )

    assert first.status_code == 202
    assert conflict.status_code == 409
    assert real.status_code == 400
    assert real.json()["detail"]["code"] == "external_processing_not_confirmed"


def test_vector_insight_is_not_queued_when_profile_is_disabled() -> None:
    repository = InMemoryInsightRepository()
    app.dependency_overrides[get_insight_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/insights",
            json={
                "document_id": str(uuid4()),
                "question": "Pergunta vetorial",
                "retrieval_mode": "vector",
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "vector_search_unavailable"
    assert repository.insights == {}
