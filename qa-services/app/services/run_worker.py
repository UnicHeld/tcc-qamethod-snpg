import asyncio
import logging
from dataclasses import replace
from typing import Protocol
from uuid import UUID

from app.core.config import Settings
from app.domain.evaluation import DocumentRevision
from app.domain.runs import StoredRun
from app.schemas.evaluation import EvaluationMode
from app.services.document_service import DocumentRepositoryError
from app.services.evaluation_service import (
    EvaluationExecution,
    ProviderError,
    ProviderModelUnavailableError,
    ProviderQuotaExceededError,
    PROMPT_VERSION,
    create_evaluation_adapter,
    finalize_evaluation,
)
from app.services.run_service import RunRepositoryError

logger = logging.getLogger(__name__)


class RunConfigurationUnavailableError(Exception):
    pass


class WorkerRunRepository(Protocol):
    def claim_next(self) -> StoredRun | None: ...

    def succeed(self, run_id: UUID, execution: EvaluationExecution) -> StoredRun: ...

    def fail(self, run_id: UUID, error_code: str, error_message: str) -> StoredRun: ...

    def interrupt_running(self) -> int: ...


class RevisionRepository(Protocol):
    def get_revision(self, document_id: str) -> DocumentRevision: ...


class RunWorker:
    def __init__(
        self,
        run_repository: WorkerRunRepository,
        revision_repository: RevisionRepository,
        settings: Settings,
    ) -> None:
        self.run_repository = run_repository
        self.revision_repository = revision_repository
        self.settings = settings

    def reconcile_interrupted(self) -> int:
        return self.run_repository.interrupt_running()

    def run_once(self) -> bool:
        run = self.run_repository.claim_next()
        if run is None:
            return False

        logger.info("run_claimed run_id=%s mode=%s", run.id, run.mode)
        try:
            revision = self.revision_repository.get_revision(str(run.document_id))
            execution = asyncio.run(self._evaluate(run, revision))
            self.run_repository.succeed(run.id, execution)
            logger.info("run_succeeded run_id=%s", run.id)
        except TimeoutError:
            self._fail(run.id, "provider_timeout", "A avaliação excedeu o tempo limite.")
        except ProviderQuotaExceededError as error:
            self._fail(run.id, "provider_quota_exceeded", str(error))
        except ProviderModelUnavailableError as error:
            self._fail(run.id, "provider_model_unavailable", str(error))
        except ProviderError as error:
            self._fail(run.id, "provider_error", str(error))
        except RunConfigurationUnavailableError as error:
            self._fail(run.id, "run_configuration_unavailable", str(error))
        except DocumentRepositoryError:
            self._fail(run.id, "document_unavailable", "O documento não pôde ser reaberto.")
        except Exception as error:
            logger.error(
                "run_worker_error run_id=%s error_type=%s",
                run.id,
                type(error).__name__,
            )
            self._fail(run.id, "worker_error", "O worker não concluiu a avaliação.")
        return True

    async def _evaluate(
        self, run: StoredRun, revision: DocumentRevision
    ) -> EvaluationExecution:
        if run.prompt_version != PROMPT_VERSION:
            raise RunConfigurationUnavailableError(
                "A versão de prompt registrada não está disponível neste worker."
            )
        mode = EvaluationMode(run.mode)
        execution_settings = replace(self.settings, gemini_model=run.model)
        adapter = create_evaluation_adapter(mode, execution_settings)
        if adapter.provider != run.provider or adapter.model != run.model:
            raise RunConfigurationUnavailableError(
                "O provedor ou modelo registrado não está disponível neste worker."
            )
        timeout_seconds = getattr(self.settings, "llm_timeout_seconds")
        async with asyncio.timeout(timeout_seconds):
            generation = await adapter.generate(revision)
        return finalize_evaluation(revision, adapter, generation)

    def _fail(self, run_id: UUID, code: str, message: str) -> None:
        try:
            self.run_repository.fail(run_id, code, message)
            logger.warning("run_failed run_id=%s error_code=%s", run_id, code)
        except RunRepositoryError:
            logger.error("run_failure_persistence_error run_id=%s", run_id)
            raise
