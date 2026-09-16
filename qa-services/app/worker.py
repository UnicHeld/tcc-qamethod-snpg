import logging
import signal
from threading import Event

from app.adapters.fastembed_text import FastEmbedTextEmbedder
from app.adapters.postgres_documents import PostgresDocumentRepository
from app.adapters.postgres_insights import PostgresInsightRunRepository
from app.adapters.postgres_runs import PostgresRunRepository
from app.adapters.postgres_search import PostgresSearchRepository
from app.core.config import get_settings
from app.core.migrations import apply_migrations
from app.domain.search import EmbeddingProfile
from app.services.insight_worker import InsightWorker
from app.services.run_worker import RunWorker

POLL_SECONDS = 1.0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL é obrigatória para executar o worker.")

    stop_event = Event()

    def request_stop(signum: int, frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    apply_migrations(settings.database_url)
    document_repository = PostgresDocumentRepository(settings.database_url)
    run_repository = PostgresRunRepository(settings.database_url)
    worker = RunWorker(
        run_repository=run_repository,
        revision_repository=document_repository,
        settings=settings,
    )
    insight_repository = PostgresInsightRunRepository(settings.database_url)
    insight_worker = InsightWorker(
        insight_repository=insight_repository,
        revision_repository=document_repository,
        search_repository=PostgresSearchRepository(settings.database_url),
        settings=settings,
        embedder_factory=lambda: FastEmbedTextEmbedder(
            EmbeddingProfile(
                model=settings.embedding_model,
                dimension=settings.embedding_dimension,
                chunk_version=settings.embedding_chunk_version,
                max_tokens=settings.embedding_max_tokens,
                overlap_tokens=settings.embedding_overlap_tokens,
            ),
            settings.embedding_cache_dir,
        ),
    )
    interrupted_count = worker.reconcile_interrupted()
    interrupted_insights = insight_worker.reconcile_interrupted()
    logging.info(
        "worker_started interrupted_runs=%s interrupted_insights=%s",
        interrupted_count,
        interrupted_insights,
    )

    while not stop_event.is_set():
        evaluation_processed = worker.run_once()
        insight_processed = insight_worker.run_once()
        if not evaluation_processed and not insight_processed:
            stop_event.wait(POLL_SECONDS)
    logging.info("worker_stopped")


if __name__ == "__main__":
    main()
