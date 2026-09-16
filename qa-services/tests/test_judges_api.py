import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.domain.evaluation import Dimension, DimensionResult, EvaluationReport
from app.domain.judges import (
    JudgeEvidenceItem,
    JudgeEvidencePackage,
    StoredJudgeRun,
)
from app.domain.runs import RunStatus
from app.main import app
from app.routers.judges import get_judge_repository
from app.services.judge_run_service import JudgeRunConflictError, JudgeRunNotFoundError
from app.services.judge_service import (
    DemoJudgeAdapter,
    finalize_judge,
    report_sha256,
)


def source_report() -> EvaluationReport:
    revision = "c" * 64
    return EvaluationReport(
        revision_sha256=revision,
        simulated=True,
        title="Parecer fonte",
        summary="Resumo",
        dimensions=tuple(
            DimensionResult(
                dimension=dimension,
                insufficient=False,
                score=5.0,
                justification="Justificativa",
                evidence_ids=(f"{revision}:page:1",),
            )
            for dimension in Dimension
        ),
    )


class InMemoryJudgeRepository:
    def __init__(self) -> None:
        self.judge_runs: dict[UUID, StoredJudgeRun] = {}
        self.by_key: dict[str, StoredJudgeRun] = {}

    def enqueue(
        self,
        source_run_id,
        mode,
        provider,
        model,
        prompt_version,
        idempotency_key,
    ):
        parsed_source_id = UUID(source_run_id)
        if idempotency_key in self.by_key:
            existing = self.by_key[idempotency_key]
            if existing.source_run_id != parsed_source_id:
                raise JudgeRunConflictError(
                    "Idempotency-Key já foi usada com outra solicitação."
                )
            return existing
        source = source_report()
        document_id = uuid4()
        evidence = JudgeEvidencePackage(
            document_id=document_id,
            revision_sha256=source.revision_sha256,
            source_report_sha256=report_sha256(source),
            items=(
                JudgeEvidenceItem(
                    unit_id=source.dimensions[0].evidence_ids[0],
                    page=1,
                    text="Evidência congelada.",
                ),
            ),
        )
        judge_run = StoredJudgeRun(
            id=uuid4(),
            source_run_id=parsed_source_id,
            document_id=document_id,
            mode=mode.value,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            status=RunStatus.QUEUED,
            source_report_sha256=report_sha256(source),
            source_report=source.model_dump(mode="json"),
            source_evidence=evidence.model_dump(mode="json"),
            usage_kind=None,
            credential_slot=None,
            input_tokens=None,
            output_tokens=None,
            report=None,
            result_markdown=None,
            error_code=None,
            error_message=None,
            created_at=datetime.now(UTC),
            started_at=None,
            finished_at=None,
        )
        self.judge_runs[judge_run.id] = judge_run
        if idempotency_key:
            self.by_key[idempotency_key] = judge_run
        return judge_run

    def get(self, judge_run_id):
        try:
            return self.judge_runs[UUID(judge_run_id)]
        except (KeyError, ValueError) as error:
            raise JudgeRunNotFoundError("Judge não encontrado.") from error

    def list_judge_runs(self, source_run_id=None):
        judge_runs = tuple(reversed(tuple(self.judge_runs.values())))
        if source_run_id is None:
            return judge_runs
        return tuple(
            item for item in judge_runs if item.source_run_id == UUID(source_run_id)
        )


def setup_function() -> None:
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def teardown_function() -> None:
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def test_judge_endpoints_are_idempotent_and_publish_only_valid_result() -> None:
    repository = InMemoryJudgeRepository()
    app.dependency_overrides[get_judge_repository] = lambda: repository
    source_run_id = uuid4()
    request = {"source_run_id": str(source_run_id), "mode": "demo"}

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/judge-runs",
            json=request,
            headers={"Idempotency-Key": "judge-1"},
        )
        duplicate = client.post(
            "/api/v1/judge-runs",
            json=request,
            headers={"Idempotency-Key": "judge-1"},
        )
        judge_run_id = UUID(created.json()["id"])
        pending = client.get(f"/api/v1/judge-runs/{judge_run_id}/result")

        source = source_report()
        evidence = JudgeEvidencePackage.model_validate(
            repository.judge_runs[judge_run_id].source_evidence
        )
        adapter = DemoJudgeAdapter()
        generation = asyncio.run(adapter.generate(source, evidence))
        execution = finalize_judge(
            source_run_id, source, evidence, adapter, generation
        )
        repository.judge_runs[judge_run_id] = replace(
            repository.judge_runs[judge_run_id],
            status=RunStatus.SUCCEEDED,
            usage_kind="simulated",
            report=execution.report.model_dump(mode="json"),
            result_markdown=execution.markdown,
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        result = client.get(f"/api/v1/judge-runs/{judge_run_id}/result")
        listed = client.get(
            "/api/v1/judge-runs", params={"source_run_id": str(source_run_id)}
        )

    assert created.status_code == 202
    assert duplicate.json()["id"] == str(judge_run_id)
    assert pending.status_code == 409
    assert result.status_code == 200
    assert result.json()["report"]["findings"][0]["id"] == "J1"
    assert result.json()["source_report"]["title"] == "Parecer fonte"
    assert result.json()["source_evidence"]["items"][0]["page"] == 1
    assert [item["id"] for item in listed.json()["judge_runs"]] == [str(judge_run_id)]


def test_judge_real_mode_requires_confirmation_before_enqueue() -> None:
    repository = InMemoryJudgeRepository()
    app.dependency_overrides[get_judge_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/judge-runs",
            json={"source_run_id": str(uuid4()), "mode": "real"},
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "external_processing_not_confirmed"
    assert repository.judge_runs == {}


def test_judge_real_mode_requires_distinct_configured_model() -> None:
    repository = InMemoryJudgeRepository()
    app.dependency_overrides[get_judge_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/judge-runs",
            json={
                "source_run_id": str(uuid4()),
                "mode": "real",
                "confirm_external_processing": True,
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "provider_unavailable"
    assert repository.judge_runs == {}


def test_judge_real_mode_enqueues_with_explicit_distinct_model() -> None:
    repository = InMemoryJudgeRepository()
    app.dependency_overrides[get_judge_repository] = lambda: repository
    app.dependency_overrides[get_settings] = lambda: Settings(
        gemini_model="generator-model",
        gemini_judge_model="judge-model",
        allowed_gemini_models=("generator-model", "judge-model"),
        google_api_key="test-key",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/judge-runs",
            json={
                "source_run_id": str(uuid4()),
                "mode": "real",
                "confirm_external_processing": True,
            },
        )

    assert response.status_code == 202
    assert response.json()["mode"] == "real"
    assert response.json()["model"] == "judge-model"
