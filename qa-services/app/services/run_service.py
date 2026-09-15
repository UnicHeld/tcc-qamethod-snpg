from typing import Protocol

from app.domain.runs import StoredRun
from app.schemas.evaluation import EvaluationMode


class RunNotFoundError(Exception):
    pass


class RunConflictError(Exception):
    pass


class RunNotReadyError(Exception):
    pass


class RunRepositoryError(Exception):
    pass


class RunRepository(Protocol):
    def enqueue(
        self,
        document_id: str,
        mode: EvaluationMode,
        provider: str,
        model: str,
        prompt_version: str,
        idempotency_key: str | None,
    ) -> StoredRun: ...

    def get(self, run_id: str) -> StoredRun: ...

    def list_runs(self, document_id: str | None = None) -> tuple[StoredRun, ...]: ...


class RunService:
    def __init__(self, repository: RunRepository) -> None:
        self.repository = repository

    def create(
        self,
        document_id: str,
        mode: EvaluationMode,
        provider: str,
        model: str,
        prompt_version: str,
        idempotency_key: str | None,
    ) -> StoredRun:
        normalized_key = idempotency_key.strip() if idempotency_key else None
        if normalized_key is not None and not 1 <= len(normalized_key) <= 128:
            raise RunConflictError("Idempotency-Key deve conter entre 1 e 128 caracteres.")
        return self.repository.enqueue(
            document_id=document_id,
            mode=mode,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            idempotency_key=normalized_key,
        )
