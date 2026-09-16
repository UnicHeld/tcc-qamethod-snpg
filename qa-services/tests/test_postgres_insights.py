import os
from uuid import uuid4

import psycopg
import pytest

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.adapters.postgres_insights import PostgresInsightRunRepository
from app.adapters.postgres_search import PostgresSearchRepository
from app.core.config import Settings
from app.core.migrations import apply_migrations
from app.domain.runs import RunStatus
from app.schemas.evaluation import EvaluationMode
from app.services.insight_run_service import InsightRunConflictError
from app.services.insight_service import INSIGHT_PROMPT_VERSION
from app.services.insight_worker import InsightWorker
from app.services.parser_service import ParserService
from tests.pdf_factory import synthetic_pdf


@pytest.mark.database
def test_postgres_insight_queue_is_idempotent_and_persists_frozen_result() -> None:
    database_url = os.environ["DATABASE_URL"]
    apply_migrations(database_url)
    documents = PostgresDocumentRepository(database_url)
    insights = PostgresInsightRunRepository(database_url)
    marker = uuid4().hex
    document = documents.save(
        "insight.pdf",
        ParserService().extract_text(
            synthetic_pdf(f"Entrevistas semiestruturadas {marker}.")
        ),
    )

    try:
        parameters = dict(
            document_id=str(document.id),
            question="Entrevistas",
            retrieval_mode="lexical",
            retrieval_limit=5,
            mode=EvaluationMode.DEMO,
            provider="local",
            model="deterministic-rag-demo-v1",
            prompt_version=INSIGHT_PROMPT_VERSION,
            idempotency_key=f"insight-{marker}",
        )
        first = insights.enqueue(**parameters)
        duplicate = insights.enqueue(**parameters)

        assert duplicate.id == first.id
        assert insights.list_insights(str(document.id))[0].id == first.id
        with pytest.raises(InsightRunConflictError):
            insights.enqueue(**{**parameters, "question": "Outra pergunta"})

        worker = InsightWorker(
            insights,
            documents,
            PostgresSearchRepository(database_url),
            Settings(database_url=database_url),
        )
        assert worker.run_once() is True
        completed = insights.get(str(first.id))

        assert completed.status is RunStatus.SUCCEEDED
        assert completed.usage_kind == "simulated"
        assert completed.evidence_package is not None
        assert completed.evidence_package["items"][0]["unit_id"]
        assert completed.report is not None
        assert completed.report["citation_ids"] == ["E1"]
        assert completed.result_markdown

        interrupted_source = insights.enqueue(
            **{**parameters, "idempotency_key": f"interrupted-{marker}"}
        )
        claimed = insights.claim_next()
        assert claimed is not None and claimed.id == interrupted_source.id
        assert insights.interrupt_running() == 1
        interrupted = insights.get(str(interrupted_source.id))
        assert interrupted.status is RunStatus.INTERRUPTED
    finally:
        with psycopg.connect(database_url) as connection:
            connection.execute("DELETE FROM documents WHERE id = %s", (document.id,))
