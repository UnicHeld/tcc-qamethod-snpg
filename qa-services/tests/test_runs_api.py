from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.domain.evaluation import Dimension, DimensionResult, EvaluationReport
from app.domain.runs import RunStatus, StoredRun
from app.main import app
from app.routers.runs import get_run_repository
from app.services.run_service import RunConflictError, RunNotFoundError


class InMemoryRunRepository:
    def __init__(self) -> None:
        self.runs: dict[UUID, StoredRun] = {}
        self.by_key: dict[str, StoredRun] = {}

    def enqueue(
        self,
        document_id,
        mode,
        provider,
        model,
        prompt_version,
        idempotency_key,
    ):
        if idempotency_key in self.by_key:
            existing = self.by_key[idempotency_key]
            if existing.document_id != UUID(document_id) or existing.mode != mode.value:
                raise RunConflictError("Idempotency-Key já foi usada com outra solicitação.")
            return existing
        run = StoredRun(
            id=uuid4(),
            document_id=UUID(document_id),
            mode=mode.value,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            status=RunStatus.QUEUED,
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
        self.runs[run.id] = run
        if idempotency_key:
            self.by_key[idempotency_key] = run
        return run

    def get(self, run_id):
        try:
            return self.runs[UUID(run_id)]
        except (KeyError, ValueError) as error:
            raise RunNotFoundError("Run não encontrado.") from error

    def list_runs(self, document_id=None):
        runs = tuple(reversed(tuple(self.runs.values())))
        if document_id is None:
            return runs
        return tuple(run for run in runs if run.document_id == UUID(document_id))


def setup_function() -> None:
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def teardown_function() -> None:
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def test_run_endpoints_are_idempotent_and_publish_result_only_after_success() -> None:
    repository = InMemoryRunRepository()
    app.dependency_overrides[get_run_repository] = lambda: repository
    document_id = uuid4()
    request = {"document_id": str(document_id), "mode": "demo"}

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/runs", json=request, headers={"Idempotency-Key": "request-1"}
        )
        duplicate = client.post(
            "/api/v1/runs", json=request, headers={"Idempotency-Key": "request-1"}
        )
        run_id = created.json()["id"]
        reopened = client.get(f"/api/v1/runs/{run_id}")
        pending_result = client.get(f"/api/v1/runs/{run_id}/result")

        report = EvaluationReport(
            revision_sha256="a" * 64,
            simulated=True,
            title="Parecer persistido",
            summary="Resumo persistido.",
            dimensions=tuple(
                DimensionResult(
                    dimension=dimension,
                    insufficient=True,
                    score=None,
                    justification="Fixture sem evidência suficiente.",
                )
                for dimension in Dimension
            ),
        )
        repository.runs[UUID(run_id)] = replace(
            repository.runs[UUID(run_id)],
            status=RunStatus.SUCCEEDED,
            usage_kind="simulated",
            report=report.model_dump(mode="json"),
            result_markdown="# Parecer persistido\n",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        result = client.get(f"/api/v1/runs/{run_id}/result")

    assert created.status_code == 202
    assert duplicate.status_code == 202
    assert duplicate.json()["id"] == run_id
    assert reopened.json()["status"] == "queued"
    assert pending_result.status_code == 409
    assert pending_result.json()["detail"]["code"] == "run_result_unavailable"
    assert result.status_code == 200
    assert result.json()["report"]["title"] == "Parecer persistido"


def test_run_endpoint_rejects_idempotency_key_reuse_with_other_request() -> None:
    repository = InMemoryRunRepository()
    app.dependency_overrides[get_run_repository] = lambda: repository

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/runs",
            json={"document_id": str(uuid4()), "mode": "demo"},
            headers={"Idempotency-Key": "same-key"},
        )
        conflict = client.post(
            "/api/v1/runs",
            json={"document_id": str(uuid4()), "mode": "demo"},
            headers={"Idempotency-Key": "same-key"},
        )

    assert first.status_code == 202
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "idempotency_conflict"


def test_run_endpoint_lists_recent_runs_and_filters_by_document() -> None:
    repository = InMemoryRunRepository()
    app.dependency_overrides[get_run_repository] = lambda: repository
    first_document_id = uuid4()
    second_document_id = uuid4()

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/runs",
            json={"document_id": str(first_document_id), "mode": "demo"},
        )
        second = client.post(
            "/api/v1/runs",
            json={"document_id": str(second_document_id), "mode": "demo"},
        )
        all_runs = client.get("/api/v1/runs")
        filtered = client.get(
            "/api/v1/runs",
            params={"document_id": str(first_document_id)},
        )

    assert first.status_code == 202
    assert second.status_code == 202
    assert [item["id"] for item in all_runs.json()["runs"]] == [
        second.json()["id"],
        first.json()["id"],
    ]
    assert [item["id"] for item in filtered.json()["runs"]] == [first.json()["id"]]


def test_real_run_requires_external_processing_confirmation() -> None:
    repository = InMemoryRunRepository()
    app.dependency_overrides[get_run_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/runs",
            json={
                "document_id": str(uuid4()),
                "mode": "real",
                "confirm_external_processing": False,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "external_processing_not_confirmed"


def test_real_run_without_provider_configuration_is_not_queued(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    repository = InMemoryRunRepository()
    app.dependency_overrides[get_run_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/runs",
            json={
                "document_id": str(uuid4()),
                "mode": "real",
                "confirm_external_processing": True,
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "provider_unavailable"
    assert repository.runs == {}


def test_run_endpoint_cors_allows_idempotency_header() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/runs",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,idempotency-key",
            },
        )

    assert response.status_code == 200
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()
