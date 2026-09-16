import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from app.domain.insights import StoredInsightRun
from app.domain.runs import RunStatus
from app.schemas.evaluation import EvaluationMode
from app.services.insight_run_service import (
    InsightRunConflictError,
    InsightRunNotFoundError,
    InsightRunRepositoryError,
)
from app.services.insight_service import InsightExecution


class PostgresInsightRunRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

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
    ) -> StoredInsightRun:
        parsed_document_id = self._parse_uuid(document_id, "Documento não encontrado.")
        insight_id = uuid4()
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                if not connection.execute(
                    "SELECT 1 FROM documents WHERE id = %s", (parsed_document_id,)
                ).fetchone():
                    raise InsightRunNotFoundError("Documento não encontrado.")

                row = connection.execute(
                    """
                    INSERT INTO rag_insight_runs (
                        id, document_id, idempotency_key, question, retrieval_mode,
                        retrieval_limit, mode, provider, model, prompt_version, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'queued')
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING *
                    """,
                    (
                        insight_id,
                        parsed_document_id,
                        idempotency_key,
                        question,
                        retrieval_mode,
                        retrieval_limit,
                        mode.value,
                        provider,
                        model,
                        prompt_version,
                    ),
                ).fetchone()
                if row is not None:
                    return self._insight_from_row(row)
                if idempotency_key is None:
                    raise InsightRunRepositoryError("O banco não retornou o insight criado.")

                existing = connection.execute(
                    "SELECT * FROM rag_insight_runs WHERE idempotency_key = %s",
                    (idempotency_key,),
                ).fetchone()
                if existing is None:
                    raise InsightRunRepositoryError("O insight idempotente não foi localizado.")
                expected = (
                    parsed_document_id,
                    question,
                    retrieval_mode,
                    retrieval_limit,
                    mode.value,
                    provider,
                    model,
                    prompt_version,
                )
                observed = tuple(
                    existing[field]
                    for field in (
                        "document_id",
                        "question",
                        "retrieval_mode",
                        "retrieval_limit",
                        "mode",
                        "provider",
                        "model",
                        "prompt_version",
                    )
                )
                if observed != expected:
                    raise InsightRunConflictError(
                        "Idempotency-Key já foi usada com outra solicitação."
                    )
                return self._insight_from_row(existing)
        except (
            InsightRunConflictError,
            InsightRunNotFoundError,
            InsightRunRepositoryError,
        ):
            raise
        except psycopg.Error as error:
            raise InsightRunRepositoryError("A persistência do insight falhou.") from error

    def get(self, insight_id: str) -> StoredInsightRun:
        parsed_id = self._parse_uuid(insight_id, "Insight não encontrado.")
        rows = self._fetch_all("SELECT * FROM rag_insight_runs WHERE id = %s", (parsed_id,))
        if not rows:
            raise InsightRunNotFoundError("Insight não encontrado.")
        return self._insight_from_row(rows[0])

    def list_insights(self, document_id: str | None = None) -> tuple[StoredInsightRun, ...]:
        if document_id is None:
            rows = self._fetch_all(
                """
                SELECT * FROM rag_insight_runs
                ORDER BY created_at DESC, id DESC
                LIMIT 100
                """
            )
        else:
            parsed_document_id = self._parse_uuid(document_id, "Documento não encontrado.")
            rows = self._fetch_all(
                """
                SELECT * FROM rag_insight_runs
                WHERE document_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 100
                """,
                (parsed_document_id,),
            )
        return tuple(self._insight_from_row(row) for row in rows)

    def claim_next(self) -> StoredInsightRun | None:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    UPDATE rag_insight_runs
                    SET status = 'running', started_at = now()
                    WHERE id = (
                        SELECT id FROM rag_insight_runs
                        WHERE status = 'queued'
                        ORDER BY created_at, id
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    RETURNING *
                    """
                ).fetchone()
                return self._insight_from_row(row) if row else None
        except psycopg.Error as error:
            raise InsightRunRepositoryError(
                "Não foi possível reivindicar o próximo insight."
            ) from error

    def succeed(self, insight_id: UUID, execution: InsightExecution) -> StoredInsightRun:
        package_json = json.dumps(execution.evidence_package.model_dump(mode="json"))
        report_json = json.dumps(execution.report.model_dump(mode="json"))
        return self._finish(
            insight_id,
            """
            UPDATE rag_insight_runs
            SET status = 'succeeded', usage_kind = %s, credential_slot = %s,
                input_tokens = %s, output_tokens = %s, evidence_package = %s::jsonb,
                report = %s::jsonb, result_markdown = %s, finished_at = now()
            WHERE id = %s AND status = 'running'
            RETURNING *
            """,
            (
                execution.usage_kind.value,
                execution.credential_slot.value if execution.credential_slot else None,
                execution.input_tokens,
                execution.output_tokens,
                package_json,
                report_json,
                execution.markdown,
                insight_id,
            ),
        )

    def fail(self, insight_id: UUID, error_code: str, error_message: str) -> StoredInsightRun:
        return self._finish(
            insight_id,
            """
            UPDATE rag_insight_runs
            SET status = 'failed', error_code = %s, error_message = %s, finished_at = now()
            WHERE id = %s AND status = 'running'
            RETURNING *
            """,
            (error_code, error_message, insight_id),
        )

    def interrupt_running(self) -> int:
        try:
            with psycopg.connect(self.database_url) as connection:
                cursor = connection.execute(
                    """
                    UPDATE rag_insight_runs
                    SET status = 'interrupted', error_code = 'worker_interrupted',
                        error_message = 'O worker anterior foi interrompido.',
                        finished_at = now()
                    WHERE status = 'running'
                    """
                )
                return cursor.rowcount
        except psycopg.Error as error:
            raise InsightRunRepositoryError(
                "Não foi possível reconciliar insights interrompidos."
            ) from error

    def _finish(
        self, insight_id: UUID, query: str, parameters: Sequence[object]
    ) -> StoredInsightRun:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                row = connection.execute(query, parameters).fetchone()
                if row is None:
                    raise InsightRunConflictError("O insight não está no estado running.")
                return self._insight_from_row(row)
        except InsightRunConflictError:
            raise
        except psycopg.Error as error:
            raise InsightRunRepositoryError("Não foi possível concluir o insight.") from error

    def _fetch_all(
        self, query: str, parameters: Sequence[object] | None = None
    ) -> list[dict[str, Any]]:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                return list(connection.execute(query, parameters or ()).fetchall())
        except psycopg.Error as error:
            raise InsightRunRepositoryError("A consulta de insights falhou.") from error

    @staticmethod
    def _parse_uuid(value: str, message: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as error:
            raise InsightRunNotFoundError(message) from error

    @staticmethod
    def _insight_from_row(row: dict[str, Any]) -> StoredInsightRun:
        package = row["evidence_package"]
        report = row["report"]
        if isinstance(package, str):
            package = json.loads(package)
        if isinstance(report, str):
            report = json.loads(report)
        return StoredInsightRun(
            id=row["id"],
            document_id=row["document_id"],
            question=row["question"],
            retrieval_mode=row["retrieval_mode"],
            retrieval_limit=row["retrieval_limit"],
            mode=row["mode"],
            provider=row["provider"],
            model=row["model"],
            prompt_version=row["prompt_version"],
            status=RunStatus(row["status"]),
            usage_kind=row["usage_kind"],
            credential_slot=row["credential_slot"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            evidence_package=package,
            report=report,
            result_markdown=row["result_markdown"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )
