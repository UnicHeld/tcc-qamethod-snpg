import os
from uuid import uuid4

import psycopg
import pytest

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.adapters.postgres_judges import PostgresJudgeRunRepository
from app.adapters.postgres_runs import PostgresRunRepository
from app.core.config import Settings
from app.core.migrations import apply_migrations
from app.domain.runs import RunStatus
from app.schemas.evaluation import EvaluationMode
from app.services.evaluation_service import PROMPT_VERSION
from app.services.judge_run_service import JudgeRunConflictError
from app.services.judge_service import JUDGE_PROMPT_VERSION
from app.services.judge_worker import JudgeWorker
from app.services.parser_service import ParserService
from app.services.run_worker import RunWorker
from tests.pdf_factory import synthetic_pdf


@pytest.mark.database
def test_postgres_judge_queue_freezes_source_and_persists_separate_result() -> None:
    database_url = os.environ["DATABASE_URL"]
    apply_migrations(database_url)
    documents = PostgresDocumentRepository(database_url)
    runs = PostgresRunRepository(database_url)
    judges = PostgresJudgeRunRepository(database_url)
    marker = uuid4().hex
    document = documents.save(
        "judge.pdf",
        ParserService().extract_text(synthetic_pdf(f"Judge PostgreSQL {marker}.")),
    )

    try:
        source = runs.enqueue(
            document_id=str(document.id),
            mode=EvaluationMode.DEMO,
            provider="local",
            model="deterministic-demo-v1",
            prompt_version=PROMPT_VERSION,
            idempotency_key=f"judge-source-{marker}",
        )
        assert RunWorker(
            runs, documents, Settings(database_url=database_url)
        ).run_once()
        source_before = runs.get(str(source.id))

        parameters = dict(
            source_run_id=str(source.id),
            mode=EvaluationMode.DEMO,
            provider="local",
            model="deterministic-judge-demo-v1",
            prompt_version=JUDGE_PROMPT_VERSION,
            idempotency_key=f"judge-{marker}",
        )
        first = judges.enqueue(**parameters)
        duplicate = judges.enqueue(**parameters)

        assert duplicate.id == first.id
        assert judges.list_judge_runs(str(source.id))[0].id == first.id
        with pytest.raises(JudgeRunConflictError):
            judges.enqueue(
                **{
                    **parameters,
                    "model": "outro-modelo",
                }
            )

        assert JudgeWorker(judges, Settings(database_url=database_url)).run_once() is True
        completed = judges.get(str(first.id))
        source_after = runs.get(str(source.id))

        assert completed.status is RunStatus.SUCCEEDED
        assert completed.usage_kind == "simulated"
        assert completed.source_evidence["items"][0]["text"]
        assert completed.report is not None
        assert completed.report["findings"][0]["id"] == "J1"
        assert completed.result_markdown
        assert source_after.report == source_before.report

        interrupted_source = judges.enqueue(
            **{**parameters, "idempotency_key": f"judge-interrupted-{marker}"}
        )
        claimed = judges.claim_next()
        assert claimed is not None and claimed.id == interrupted_source.id
        assert judges.interrupt_running() == 1
        assert judges.get(str(interrupted_source.id)).status is RunStatus.INTERRUPTED
    finally:
        with psycopg.connect(database_url) as connection:
            connection.execute("DELETE FROM documents WHERE id = %s", (document.id,))
