from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import Settings
from app.domain.evaluation import Dimension, DimensionResult, EvaluationReport
from app.domain.judges import (
    JudgeEvidenceItem,
    JudgeEvidencePackage,
    StoredJudgeRun,
)
from app.domain.runs import RunStatus
from app.services.judge_service import JUDGE_PROMPT_VERSION, report_sha256
from app.services.judge_worker import JudgeWorker


def source_report() -> EvaluationReport:
    revision = "b" * 64
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
                justification="Justificativa simulada.",
                evidence_ids=(f"{revision}:page:1",),
            )
            for dimension in Dimension
        ),
    )


def queued_judge() -> StoredJudgeRun:
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
    return StoredJudgeRun(
        id=uuid4(),
        source_run_id=uuid4(),
        document_id=document_id,
        mode="demo",
        provider="local",
        model="deterministic-judge-demo-v1",
        prompt_version=JUDGE_PROMPT_VERSION,
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


class InMemoryJudgeRepository:
    def __init__(self, judge_run: StoredJudgeRun) -> None:
        self.judge_run = judge_run
        self.execution = None
        self.failure = None

    def claim_next(self):
        if self.judge_run.status is not RunStatus.QUEUED:
            return None
        self.judge_run = replace(
            self.judge_run, status=RunStatus.RUNNING, started_at=datetime.now(UTC)
        )
        return self.judge_run

    def succeed(self, judge_run_id, execution):
        self.execution = execution
        self.judge_run = replace(self.judge_run, status=RunStatus.SUCCEEDED)
        return self.judge_run

    def fail(self, judge_run_id, error_code, error_message):
        self.failure = (error_code, error_message)
        self.judge_run = replace(self.judge_run, status=RunStatus.FAILED)
        return self.judge_run

    def interrupt_running(self):
        if self.judge_run.status is not RunStatus.RUNNING:
            return 0
        self.judge_run = replace(self.judge_run, status=RunStatus.INTERRUPTED)
        return 1


def test_worker_persists_demo_judge_without_changing_source_snapshot() -> None:
    judge_run = queued_judge()
    snapshot = judge_run.source_report.copy()
    repository = InMemoryJudgeRepository(judge_run)
    worker = JudgeWorker(repository, Settings())

    assert worker.run_once() is True
    assert repository.judge_run.status is RunStatus.SUCCEEDED
    assert repository.execution.report.simulated is True
    assert repository.execution.report.findings[0].id == "J1"
    assert repository.judge_run.source_report == snapshot
    assert worker.run_once() is False


def test_worker_rejects_tampered_source_snapshot() -> None:
    repository = InMemoryJudgeRepository(
        replace(queued_judge(), source_report_sha256="c" * 64)
    )

    assert JudgeWorker(repository, Settings()).run_once() is True
    assert repository.judge_run.status is RunStatus.FAILED
    assert repository.failure[0] == "run_configuration_unavailable"
    assert repository.execution is None


def test_worker_reconciles_abandoned_judge() -> None:
    repository = InMemoryJudgeRepository(
        replace(queued_judge(), status=RunStatus.RUNNING)
    )

    assert JudgeWorker(repository, Settings()).reconcile_interrupted() == 1
    assert repository.judge_run.status is RunStatus.INTERRUPTED
