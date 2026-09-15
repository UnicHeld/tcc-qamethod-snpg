import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from app.domain.runs import RunStatus, StoredRun
from app.schemas.evaluation import EvaluationMode
from app.services.evaluation_service import EvaluationExecution
from app.services.run_service import (
    RunConflictError,
    RunNotFoundError,
    RunRepositoryError,
)


class PostgresRunRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def enqueue(
        self,
        document_id: str,
        mode: EvaluationMode,
        provider: str,
        model: str,
        prompt_version: str,
        idempotency_key: str | None,
    ) -> StoredRun:
        parsed_document_id = self._parse_uuid(document_id, "Documento não encontrado.")
        run_id = uuid4()
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                if not connection.execute(
                    "SELECT 1 FROM documents WHERE id = %s", (parsed_document_id,)
                ).fetchone():
                    raise RunNotFoundError("Documento não encontrado.")

                row = connection.execute(
                    """
                    INSERT INTO evaluation_runs (
                        id, document_id, idempotency_key, mode, provider, model,
                        prompt_version, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'queued')
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING *
                    """,
                    (
                        run_id,
                        parsed_document_id,
                        idempotency_key,
                        mode.value,
                        provider,
                        model,
                        prompt_version,
                    ),
                ).fetchone()
                if row is not None:
                    return self._run_from_row(row)
                if idempotency_key is None:
                    raise RunRepositoryError("O banco não retornou o run criado.")

                existing = connection.execute(
                    "SELECT * FROM evaluation_runs WHERE idempotency_key = %s",
                    (idempotency_key,),
                ).fetchone()
                if existing is None:
                    raise RunRepositoryError("O run idempotente não foi localizado.")
                expected = (
                    parsed_document_id,
                    mode.value,
                    provider,
                    model,
                    prompt_version,
                )
                observed = tuple(
                    existing[field]
                    for field in (
                        "document_id",
                        "mode",
                        "provider",
                        "model",
                        "prompt_version",
                    )
                )
                if observed != expected:
                    raise RunConflictError(
                        "Idempotency-Key já foi usada com outra solicitação."
                    )
                return self._run_from_row(existing)
        except (RunConflictError, RunNotFoundError, RunRepositoryError):
            raise
        except psycopg.Error as error:
            raise RunRepositoryError("A persistência do run falhou.") from error

    def get(self, run_id: str) -> StoredRun:
        parsed_run_id = self._parse_uuid(run_id, "Run não encontrado.")
        rows = self._fetch_all("SELECT * FROM evaluation_runs WHERE id = %s", (parsed_run_id,))
        if not rows:
            raise RunNotFoundError("Run não encontrado.")
        return self._run_from_row(rows[0])

    def list_runs(self, document_id: str | None = None) -> tuple[StoredRun, ...]:
        if document_id is None:
            rows = self._fetch_all(
                """
                SELECT *
                FROM evaluation_runs
                ORDER BY created_at DESC, id DESC
                LIMIT 100
                """
            )
        else:
            parsed_document_id = self._parse_uuid(document_id, "Documento não encontrado.")
            rows = self._fetch_all(
                """
                SELECT *
                FROM evaluation_runs
                WHERE document_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 100
                """,
                (parsed_document_id,),
            )
        return tuple(self._run_from_row(row) for row in rows)

    def claim_next(self) -> StoredRun | None:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    UPDATE evaluation_runs
                    SET status = 'running', started_at = now()
                    WHERE id = (
                        SELECT id
                        FROM evaluation_runs
                        WHERE status = 'queued'
                        ORDER BY created_at, id
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    RETURNING *
                    """
                ).fetchone()
                return self._run_from_row(row) if row else None
        except psycopg.Error as error:
            raise RunRepositoryError("Não foi possível reivindicar o próximo run.") from error

    def succeed(self, run_id: UUID, execution: EvaluationExecution) -> StoredRun:
        report_json = json.dumps(execution.report.model_dump(mode="json"))
        return self._finish(
            run_id,
            """
            UPDATE evaluation_runs
            SET status = 'succeeded', usage_kind = %s, credential_slot = %s,
                input_tokens = %s, output_tokens = %s, report = %s::jsonb,
                result_markdown = %s, finished_at = now()
            WHERE id = %s AND status = 'running'
            RETURNING *
            """,
            (
                execution.usage_kind.value,
                execution.credential_slot.value if execution.credential_slot else None,
                execution.input_tokens,
                execution.output_tokens,
                report_json,
                execution.markdown,
                run_id,
            ),
        )

    def fail(self, run_id: UUID, error_code: str, error_message: str) -> StoredRun:
        return self._finish(
            run_id,
            """
            UPDATE evaluation_runs
            SET status = 'failed', error_code = %s, error_message = %s,
                finished_at = now()
            WHERE id = %s AND status = 'running'
            RETURNING *
            """,
            (error_code, error_message, run_id),
        )

    def interrupt_running(self) -> int:
        try:
            with psycopg.connect(self.database_url) as connection:
                cursor = connection.execute(
                    """
                    UPDATE evaluation_runs
                    SET status = 'interrupted', error_code = 'worker_interrupted',
                        error_message = 'O worker anterior foi interrompido.',
                        finished_at = now()
                    WHERE status = 'running'
                    """
                )
                return cursor.rowcount
        except psycopg.Error as error:
            raise RunRepositoryError("Não foi possível reconciliar runs interrompidos.") from error

    def _finish(
        self, run_id: UUID, query: str, parameters: Sequence[object]
    ) -> StoredRun:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                row = connection.execute(query, parameters).fetchone()
                if row is None:
                    raise RunConflictError("O run não está no estado running.")
                return self._run_from_row(row)
        except RunConflictError:
            raise
        except psycopg.Error as error:
            raise RunRepositoryError("Não foi possível concluir o run.") from error

    def _fetch_all(
        self, query: str, parameters: Sequence[object] | None = None
    ) -> list[dict[str, Any]]:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                return list(connection.execute(query, parameters or ()).fetchall())
        except psycopg.Error as error:
            raise RunRepositoryError("A consulta de runs falhou.") from error

    @staticmethod
    def _parse_uuid(value: str, message: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as error:
            raise RunNotFoundError(message) from error

    @staticmethod
    def _run_from_row(row: dict[str, Any]) -> StoredRun:
        report = row["report"]
        if isinstance(report, str):
            report = json.loads(report)
        return StoredRun(
            id=row["id"],
            document_id=row["document_id"],
            mode=row["mode"],
            provider=row["provider"],
            model=row["model"],
            prompt_version=row["prompt_version"],
            status=RunStatus(row["status"]),
            usage_kind=row["usage_kind"],
            credential_slot=row["credential_slot"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            report=report,
            result_markdown=row["result_markdown"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )
