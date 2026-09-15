from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import Settings
from app.domain.evaluation import DocumentRevision, DocumentUnit
from app.domain.runs import RunStatus, StoredRun
from app.services.run_worker import RunWorker


class InMemoryWorkerRunRepository:
    def __init__(self, run: StoredRun) -> None:
        self.run = run
        self.execution = None
        self.failure = None

    def claim_next(self):
        if self.run.status is not RunStatus.QUEUED:
            return None
        self.run = replace(
            self.run, status=RunStatus.RUNNING, started_at=datetime.now(UTC)
        )
        return self.run

    def succeed(self, run_id, execution):
        self.execution = execution
        self.run = replace(self.run, status=RunStatus.SUCCEEDED)
        return self.run

    def fail(self, run_id, error_code, error_message):
        self.failure = (error_code, error_message)
        self.run = replace(self.run, status=RunStatus.FAILED)
        return self.run

    def interrupt_running(self):
        if self.run.status is not RunStatus.RUNNING:
            return 0
        self.run = replace(self.run, status=RunStatus.INTERRUPTED)
        return 1


class InMemoryRevisionRepository:
    def __init__(self, revision: DocumentRevision) -> None:
        self.revision = revision

    def get_revision(self, document_id):
        return self.revision


def queued_run(document_id) -> StoredRun:
    return StoredRun(
        id=uuid4(),
        document_id=document_id,
        mode="demo",
        provider="local",
        model="deterministic-demo-v1",
        prompt_version="qa-method-structured-v2",
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


def test_worker_executes_one_demo_run_and_persists_validated_result() -> None:
    document_id = uuid4()
    sha256 = "b" * 64
    revision = DocumentRevision(
        sha256=sha256,
        page_count=1,
        units=(DocumentUnit(id=f"{sha256}:page:1", page=1, text="Fixture"),),
    )
    runs = InMemoryWorkerRunRepository(queued_run(document_id))
    worker = RunWorker(runs, InMemoryRevisionRepository(revision), Settings())

    assert worker.run_once() is True
    assert runs.run.status is RunStatus.SUCCEEDED
    assert runs.execution.report.revision_sha256 == sha256
    assert len(runs.execution.report.dimensions) == 6
    assert worker.run_once() is False


def test_worker_marks_abandoned_running_run_as_interrupted() -> None:
    run = replace(queued_run(uuid4()), status=RunStatus.RUNNING)
    repository = InMemoryWorkerRunRepository(run)
    worker = RunWorker(
        repository,
        InMemoryRevisionRepository(
            DocumentRevision(
                sha256="c" * 64,
                page_count=1,
                units=(
                    DocumentUnit(id=f"{'c' * 64}:page:1", page=1, text="Fixture"),
                ),
            )
        ),
        Settings(),
    )

    assert worker.reconcile_interrupted() == 1
    assert repository.run.status is RunStatus.INTERRUPTED


def test_worker_refuses_to_execute_a_different_persisted_configuration() -> None:
    document_id = uuid4()
    sha256 = "d" * 64
    revision = DocumentRevision(
        sha256=sha256,
        page_count=1,
        units=(DocumentUnit(id=f"{sha256}:page:1", page=1, text="Fixture"),),
    )
    run = replace(queued_run(document_id), model="modelo-diferente")
    repository = InMemoryWorkerRunRepository(run)
    worker = RunWorker(repository, InMemoryRevisionRepository(revision), Settings())

    assert worker.run_once() is True
    assert repository.run.status is RunStatus.FAILED
    assert repository.failure is not None
    assert repository.failure[0] == "run_configuration_unavailable"
    assert repository.execution is None
