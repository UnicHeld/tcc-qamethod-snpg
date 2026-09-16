from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import Settings
from app.domain.evaluation import DocumentRevision, DocumentUnit
from app.domain.insights import StoredInsightRun
from app.domain.runs import RunStatus
from app.domain.search import LexicalMatch
from app.services.insight_service import INSIGHT_PROMPT_VERSION
from app.services.insight_worker import InsightWorker


class InMemoryInsightRepository:
    def __init__(self, insight: StoredInsightRun) -> None:
        self.insight = insight
        self.execution = None
        self.failure = None

    def claim_next(self):
        if self.insight.status is not RunStatus.QUEUED:
            return None
        self.insight = replace(
            self.insight, status=RunStatus.RUNNING, started_at=datetime.now(UTC)
        )
        return self.insight

    def succeed(self, insight_id, execution):
        self.execution = execution
        self.insight = replace(self.insight, status=RunStatus.SUCCEEDED)
        return self.insight

    def fail(self, insight_id, error_code, error_message):
        self.failure = (error_code, error_message)
        self.insight = replace(self.insight, status=RunStatus.FAILED)
        return self.insight

    def interrupt_running(self):
        if self.insight.status is not RunStatus.RUNNING:
            return 0
        self.insight = replace(self.insight, status=RunStatus.INTERRUPTED)
        return 1


class RevisionRepository:
    def __init__(self, revision: DocumentRevision) -> None:
        self.revision = revision

    def get_revision(self, document_id):
        return self.revision


class SearchRepository:
    def __init__(self, matches) -> None:
        self.matches = matches

    def search_lexical(self, document_id, query, limit):
        return self.matches[:limit]

    def list_units(self, document_id):
        raise AssertionError("Busca lexical não indexa unidades.")

    def is_vector_indexed(self, document_id, profile):
        raise AssertionError("Busca lexical não consulta índice vetorial.")

    def replace_vector_index(self, document_id, profile, chunks):
        raise AssertionError("Busca lexical não grava índice vetorial.")

    def search_vector(self, document_id, profile, query_embedding, limit):
        raise AssertionError("Busca lexical não consulta vetores.")


def queued_insight(document_id) -> StoredInsightRun:
    return StoredInsightRun(
        id=uuid4(),
        document_id=document_id,
        question="Como os participantes foram ouvidos?",
        retrieval_mode="lexical",
        retrieval_limit=5,
        mode="demo",
        provider="local",
        model="deterministic-rag-demo-v1",
        prompt_version=INSIGHT_PROMPT_VERSION,
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


def fixture_revision() -> DocumentRevision:
    sha256 = "d" * 64
    return DocumentRevision(
        sha256=sha256,
        page_count=1,
        units=(
            DocumentUnit(
                id=f"{sha256}:page:1",
                page=1,
                text="Foram realizadas entrevistas semiestruturadas.",
            ),
        ),
    )


def test_worker_retrieves_evidence_and_persists_demo_insight() -> None:
    document_id = uuid4()
    revision = fixture_revision()
    repository = InMemoryInsightRepository(queued_insight(document_id))
    search = SearchRepository(
        (
            LexicalMatch(
                unit_id=revision.units[0].id,
                document_id=document_id,
                page=1,
                text=revision.units[0].text,
                score=0.9,
            ),
        )
    )
    worker = InsightWorker(
        repository,
        RevisionRepository(revision),
        search,
        Settings(),
    )

    assert worker.run_once() is True
    assert repository.insight.status is RunStatus.SUCCEEDED
    assert repository.execution.report.citation_ids == ("E1",)
    assert repository.execution.evidence_package.items[0].unit_id == revision.units[0].id
    assert worker.run_once() is False


def test_worker_fails_without_evidence_and_does_not_publish_partial_result() -> None:
    document_id = uuid4()
    repository = InMemoryInsightRepository(queued_insight(document_id))
    worker = InsightWorker(
        repository,
        RevisionRepository(fixture_revision()),
        SearchRepository(()),
        Settings(),
    )

    assert worker.run_once() is True
    assert repository.insight.status is RunStatus.FAILED
    assert repository.failure[0] == "insufficient_evidence"
    assert repository.execution is None


def test_worker_reconciles_abandoned_insight() -> None:
    repository = InMemoryInsightRepository(
        replace(queued_insight(uuid4()), status=RunStatus.RUNNING)
    )
    worker = InsightWorker(
        repository,
        RevisionRepository(fixture_revision()),
        SearchRepository(()),
        Settings(),
    )

    assert worker.reconcile_interrupted() == 1
    assert repository.insight.status is RunStatus.INTERRUPTED
