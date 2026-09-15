import os
from uuid import uuid4

import psycopg
import pytest

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.adapters.postgres_runs import PostgresRunRepository
from app.core.config import Settings
from app.core.migrations import apply_migrations
from app.domain.runs import RunStatus
from app.schemas.evaluation import EvaluationMode
from app.services.evaluation_service import PROMPT_VERSION
from app.services.parser_service import ParserService
from app.services.run_service import RunConflictError
from app.services.run_worker import RunWorker
from tests.pdf_factory import synthetic_pdf


@pytest.mark.database
def test_postgres_run_queue_is_idempotent_and_worker_persists_result() -> None:
    database_url = os.environ["DATABASE_URL"]
    apply_migrations(database_url)
    documents = PostgresDocumentRepository(database_url)
    runs = PostgresRunRepository(database_url)
    marker = uuid4().hex
    document = documents.save(
        "run.pdf",
        ParserService().extract_text(synthetic_pdf(f"Run PostgreSQL {marker}.")),
    )

    try:
        first = runs.enqueue(
            document_id=str(document.id),
            mode=EvaluationMode.DEMO,
            provider="local",
            model="deterministic-demo-v1",
            prompt_version=PROMPT_VERSION,
            idempotency_key=f"run-{marker}",
        )
        duplicate = runs.enqueue(
            document_id=str(document.id),
            mode=EvaluationMode.DEMO,
            provider="local",
            model="deterministic-demo-v1",
            prompt_version=PROMPT_VERSION,
            idempotency_key=f"run-{marker}",
        )

        assert duplicate.id == first.id
        assert runs.list_runs(str(document.id))[0].id == first.id
        assert first.id in {run.id for run in runs.list_runs()}
        with pytest.raises(RunConflictError):
            runs.enqueue(
                document_id=str(document.id),
                mode=EvaluationMode.DEMO,
                provider="local",
                model="outro-modelo",
                prompt_version=PROMPT_VERSION,
                idempotency_key=f"run-{marker}",
            )

        worker = RunWorker(runs, documents, Settings(database_url=database_url))
        assert worker.run_once() is True
        completed = runs.get(str(first.id))

        assert completed.status is RunStatus.SUCCEEDED
        assert completed.usage_kind == "simulated"
        assert completed.report is not None
        assert len(completed.report["dimensions"]) == 6
        assert completed.result_markdown

        interrupted_source = runs.enqueue(
            document_id=str(document.id),
            mode=EvaluationMode.DEMO,
            provider="local",
            model="deterministic-demo-v1",
            prompt_version=PROMPT_VERSION,
            idempotency_key=f"interrupted-{marker}",
        )
        claimed = runs.claim_next()
        assert claimed is not None and claimed.id == interrupted_source.id
        assert runs.interrupt_running() == 1
        interrupted = runs.get(str(interrupted_source.id))
        assert interrupted.status is RunStatus.INTERRUPTED
        assert interrupted.error_code == "worker_interrupted"
    finally:
        with psycopg.connect(database_url) as connection:
            connection.execute("DELETE FROM documents WHERE id = %s", (document.id,))
