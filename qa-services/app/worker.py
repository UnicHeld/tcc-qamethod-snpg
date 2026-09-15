import logging
import signal
from threading import Event

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.adapters.postgres_runs import PostgresRunRepository
from app.core.config import get_settings
from app.core.migrations import apply_migrations
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
    run_repository = PostgresRunRepository(settings.database_url)
    worker = RunWorker(
        run_repository=run_repository,
        revision_repository=PostgresDocumentRepository(settings.database_url),
        settings=settings,
    )
    interrupted_count = worker.reconcile_interrupted()
    logging.info("worker_started interrupted_runs=%s", interrupted_count)

    while not stop_event.is_set():
        if not worker.run_once():
            stop_event.wait(POLL_SECONDS)
    logging.info("worker_stopped")


if __name__ == "__main__":
    main()
