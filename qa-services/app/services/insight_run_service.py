from typing import Protocol

from app.domain.insights import StoredInsightRun
from app.schemas.evaluation import EvaluationMode


class InsightRunNotFoundError(Exception):
    pass


class InsightRunConflictError(Exception):
    pass


class InsightRunRepositoryError(Exception):
    pass


class InsightRunRepository(Protocol):
    def enqueue(
        self,
        document_id: str,
        question: str,
        retrieval_mode: str,
        retrieval_limit: int,
        mode: EvaluationMode,
        provider: str,
        model: str,
        prompt_version: str,
        idempotency_key: str | None,
    ) -> StoredInsightRun: ...

    def get(self, insight_id: str) -> StoredInsightRun: ...

    def list_insights(self, document_id: str | None = None) -> tuple[StoredInsightRun, ...]: ...


class InsightRunService:
    def __init__(self, repository: InsightRunRepository) -> None:
        self.repository = repository

    def create(
        self,
        document_id: str,
        question: str,
        retrieval_mode: str,
        retrieval_limit: int,
        mode: EvaluationMode,
        provider: str,
        model: str,
        prompt_version: str,
        idempotency_key: str | None,
    ) -> StoredInsightRun:
        return self.repository.enqueue(
            document_id,
            question,
            retrieval_mode,
            retrieval_limit,
            mode,
            provider,
            model,
            prompt_version,
            idempotency_key,
        )
