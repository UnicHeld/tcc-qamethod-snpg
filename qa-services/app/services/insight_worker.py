import asyncio
import logging
from dataclasses import replace
from typing import Callable, Protocol
from uuid import UUID

from app.core.config import Settings
from app.domain.evaluation import DocumentRevision
from app.domain.insights import StoredInsightRun
from app.schemas.evaluation import EvaluationMode
from app.services.document_service import DocumentNotFoundError, DocumentRepositoryError
from app.services.evaluation_service import (
    ProviderError,
    ProviderModelUnavailableError,
    ProviderQuotaExceededError,
)
from app.services.insight_run_service import InsightRunRepositoryError
from app.services.insight_service import (
    INSIGHT_PROMPT_VERSION,
    InsightExecution,
    InsufficientEvidenceError,
    build_evidence_package,
    create_insight_adapter,
    finalize_insight,
)
from app.services.search_service import (
    InvalidSearchQueryError,
    SearchRepository,
    SearchService,
    TextEmbedder,
    VectorSearchUnavailableError,
)

logger = logging.getLogger(__name__)


class InsightConfigurationUnavailableError(Exception):
    pass


class WorkerInsightRepository(Protocol):
    def claim_next(self) -> StoredInsightRun | None: ...

    def succeed(self, insight_id: UUID, execution: InsightExecution) -> StoredInsightRun: ...

    def fail(
        self, insight_id: UUID, error_code: str, error_message: str
    ) -> StoredInsightRun: ...

    def interrupt_running(self) -> int: ...


class RevisionRepository(Protocol):
    def get_revision(self, document_id: str) -> DocumentRevision: ...


class InsightWorker:
    def __init__(
        self,
        insight_repository: WorkerInsightRepository,
        revision_repository: RevisionRepository,
        search_repository: SearchRepository,
        settings: Settings,
        embedder_factory: Callable[[], TextEmbedder] | None = None,
    ) -> None:
        self.insight_repository = insight_repository
        self.revision_repository = revision_repository
        self.search_repository = search_repository
        self.settings = settings
        self.embedder_factory = embedder_factory
        self._embedder: TextEmbedder | None = None

    def reconcile_interrupted(self) -> int:
        return self.insight_repository.interrupt_running()

    def run_once(self) -> bool:
        insight = self.insight_repository.claim_next()
        if insight is None:
            return False

        logger.info(
            "insight_claimed insight_id=%s retrieval_mode=%s mode=%s",
            insight.id,
            insight.retrieval_mode,
            insight.mode,
        )
        try:
            revision = self.revision_repository.get_revision(str(insight.document_id))
            execution = asyncio.run(self._execute(insight, revision))
            self.insight_repository.succeed(insight.id, execution)
            logger.info("insight_succeeded insight_id=%s", insight.id)
        except InsufficientEvidenceError as error:
            self._fail(insight.id, "insufficient_evidence", str(error))
        except InvalidSearchQueryError as error:
            self._fail(insight.id, "invalid_question", str(error))
        except VectorSearchUnavailableError as error:
            self._fail(insight.id, "vector_search_unavailable", str(error))
        except TimeoutError:
            self._fail(insight.id, "provider_timeout", "O insight excedeu o tempo limite.")
        except ProviderQuotaExceededError as error:
            self._fail(insight.id, "provider_quota_exceeded", str(error))
        except ProviderModelUnavailableError as error:
            self._fail(insight.id, "provider_model_unavailable", str(error))
        except ProviderError as error:
            self._fail(insight.id, "provider_error", str(error))
        except InsightConfigurationUnavailableError as error:
            self._fail(insight.id, "run_configuration_unavailable", str(error))
        except (DocumentNotFoundError, DocumentRepositoryError):
            self._fail(insight.id, "document_unavailable", "O documento não pôde ser reaberto.")
        except Exception as error:
            logger.error(
                "insight_worker_error insight_id=%s error_type=%s",
                insight.id,
                type(error).__name__,
            )
            self._fail(insight.id, "worker_error", "O worker não concluiu o insight.")
        return True

    async def _execute(
        self, insight: StoredInsightRun, revision: DocumentRevision
    ) -> InsightExecution:
        if insight.prompt_version != INSIGHT_PROMPT_VERSION:
            raise InsightConfigurationUnavailableError(
                "A versão de prompt registrada não está disponível neste worker."
            )

        embedder = self._get_embedder(insight.retrieval_mode)
        result = SearchService(self.search_repository, embedder).search(
            str(insight.document_id),
            insight.question,
            insight.retrieval_limit,
            insight.retrieval_mode,
        )
        package = build_evidence_package(insight.document_id, revision, result)

        mode = EvaluationMode(insight.mode)
        execution_settings = replace(self.settings, gemini_model=insight.model)
        adapter = create_insight_adapter(mode, execution_settings)
        if adapter.provider != insight.provider or adapter.model != insight.model:
            raise InsightConfigurationUnavailableError(
                "O provedor ou modelo registrado não está disponível neste worker."
            )
        async with asyncio.timeout(self.settings.llm_timeout_seconds):
            generation = await adapter.generate(package)
        return finalize_insight(package, adapter, generation)

    def _get_embedder(self, retrieval_mode: str) -> TextEmbedder | None:
        if retrieval_mode != "vector":
            return None
        if not self.settings.vector_search_enabled or self.embedder_factory is None:
            raise VectorSearchUnavailableError("A busca vetorial local não está habilitada.")
        if self._embedder is None:
            self._embedder = self.embedder_factory()
        return self._embedder

    def _fail(self, insight_id: UUID, code: str, message: str) -> None:
        try:
            self.insight_repository.fail(insight_id, code, message)
            logger.warning("insight_failed insight_id=%s error_code=%s", insight_id, code)
        except InsightRunRepositoryError:
            logger.error("insight_failure_persistence_error insight_id=%s", insight_id)
            raise
