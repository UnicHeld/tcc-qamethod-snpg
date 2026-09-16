from typing import Protocol

from app.domain.judges import StoredJudgeRun
from app.schemas.evaluation import EvaluationMode


class JudgeRunNotFoundError(Exception):
    pass


class JudgeSourceUnavailableError(Exception):
    pass


class JudgeRunConflictError(Exception):
    pass


class JudgeRunRepositoryError(Exception):
    pass


class JudgeRunRepository(Protocol):
    def enqueue(
        self,
        source_run_id: str,
        mode: EvaluationMode,
        provider: str,
        model: str,
        prompt_version: str,
        idempotency_key: str | None,
    ) -> StoredJudgeRun: ...

    def get(self, judge_run_id: str) -> StoredJudgeRun: ...

    def list_judge_runs(
        self, source_run_id: str | None = None
    ) -> tuple[StoredJudgeRun, ...]: ...


class JudgeRunService:
    def __init__(self, repository: JudgeRunRepository) -> None:
        self.repository = repository

    def create(
        self,
        source_run_id: str,
        mode: EvaluationMode,
        provider: str,
        model: str,
        prompt_version: str,
        idempotency_key: str | None,
    ) -> StoredJudgeRun:
        return self.repository.enqueue(
            source_run_id,
            mode,
            provider,
            model,
            prompt_version,
            idempotency_key,
        )
