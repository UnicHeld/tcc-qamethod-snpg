import asyncio
import logging
from dataclasses import replace
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from app.core.config import Settings
from app.domain.evaluation import EvaluationReport
from app.domain.judges import JudgeEvidencePackage, StoredJudgeRun
from app.schemas.evaluation import EvaluationMode
from app.services.evaluation_service import (
    ProviderError,
    ProviderModelUnavailableError,
    ProviderQuotaExceededError,
)
from app.services.judge_run_service import JudgeRunRepositoryError
from app.services.judge_service import (
    JUDGE_PROMPT_VERSION,
    JudgeExecution,
    create_judge_adapter,
    finalize_judge,
    report_sha256,
)

logger = logging.getLogger(__name__)


class JudgeConfigurationUnavailableError(Exception):
    pass


class WorkerJudgeRepository(Protocol):
    def claim_next(self) -> StoredJudgeRun | None: ...

    def succeed(
        self, judge_run_id: UUID, execution: JudgeExecution
    ) -> StoredJudgeRun: ...

    def fail(
        self, judge_run_id: UUID, error_code: str, error_message: str
    ) -> StoredJudgeRun: ...

    def interrupt_running(self) -> int: ...


class JudgeWorker:
    def __init__(self, repository: WorkerJudgeRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def reconcile_interrupted(self) -> int:
        return self.repository.interrupt_running()

    def run_once(self) -> bool:
        judge_run = self.repository.claim_next()
        if judge_run is None:
            return False
        logger.info("judge_claimed judge_run_id=%s", judge_run.id)
        try:
            execution = asyncio.run(self._execute(judge_run))
            self.repository.succeed(judge_run.id, execution)
            logger.info("judge_succeeded judge_run_id=%s", judge_run.id)
        except ValidationError:
            self._fail(
                judge_run.id,
                "stored_source_invalid",
                "O parecer fonte não atende ao contrato atual.",
            )
        except TimeoutError:
            self._fail(judge_run.id, "provider_timeout", "O judge excedeu o tempo limite.")
        except ProviderQuotaExceededError as error:
            self._fail(judge_run.id, "provider_quota_exceeded", str(error))
        except ProviderModelUnavailableError as error:
            self._fail(judge_run.id, "provider_model_unavailable", str(error))
        except JudgeConfigurationUnavailableError as error:
            self._fail(judge_run.id, "run_configuration_unavailable", str(error))
        except ProviderError as error:
            self._fail(judge_run.id, "provider_error", str(error))
        except Exception as error:
            logger.error(
                "judge_worker_error judge_run_id=%s error_type=%s",
                judge_run.id,
                type(error).__name__,
            )
            self._fail(judge_run.id, "worker_error", "O worker não concluiu o judge.")
        return True

    async def _execute(self, judge_run: StoredJudgeRun) -> JudgeExecution:
        if judge_run.prompt_version != JUDGE_PROMPT_VERSION:
            raise JudgeConfigurationUnavailableError(
                "A versão registrada do judge não está disponível neste worker."
            )
        source = EvaluationReport.model_validate(judge_run.source_report)
        evidence = JudgeEvidencePackage.model_validate(judge_run.source_evidence)
        if report_sha256(source) != judge_run.source_report_sha256:
            raise JudgeConfigurationUnavailableError(
                "O snapshot do parecer fonte não corresponde ao hash registrado."
            )
        evidence.validate_source(source, judge_run.source_report_sha256)
        mode = EvaluationMode(judge_run.mode)
        execution_settings = replace(
            self.settings,
            gemini_judge_model=(
                judge_run.model if mode is EvaluationMode.REAL else None
            ),
        )
        adapter = create_judge_adapter(mode, execution_settings)
        if adapter.provider != judge_run.provider or adapter.model != judge_run.model:
            raise JudgeConfigurationUnavailableError(
                "O adaptador registrado não está disponível neste worker."
            )
        async with asyncio.timeout(self.settings.llm_timeout_seconds):
            generation = await adapter.generate(source, evidence)
        return finalize_judge(
            judge_run.source_run_id, source, evidence, adapter, generation
        )

    def _fail(self, judge_run_id: UUID, code: str, message: str) -> None:
        try:
            self.repository.fail(judge_run_id, code, message)
            logger.warning(
                "judge_failed judge_run_id=%s error_code=%s", judge_run_id, code
            )
        except JudgeRunRepositoryError:
            logger.error(
                "judge_failure_persistence_error judge_run_id=%s", judge_run_id
            )
            raise
