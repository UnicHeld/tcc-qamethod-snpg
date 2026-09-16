import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from pydantic import ValidationError

from app.domain.evaluation import EvaluationReport
from app.domain.judges import (
    JudgeEvidenceItem,
    JudgeEvidencePackage,
    StoredJudgeRun,
)
from app.domain.runs import RunStatus
from app.schemas.evaluation import EvaluationMode
from app.services.judge_run_service import (
    JudgeRunConflictError,
    JudgeRunNotFoundError,
    JudgeRunRepositoryError,
    JudgeSourceUnavailableError,
)
from app.services.judge_service import JudgeExecution, report_sha256


class PostgresJudgeRunRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def enqueue(
        self,
        source_run_id: str,
        mode: EvaluationMode,
        provider: str,
        model: str,
        prompt_version: str,
        idempotency_key: str | None,
    ) -> StoredJudgeRun:
        parsed_source_id = self._parse_uuid(source_run_id, "Parecer fonte não encontrado.")
        judge_run_id = uuid4()
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                source = connection.execute(
                    "SELECT * FROM evaluation_runs WHERE id = %s",
                    (parsed_source_id,),
                ).fetchone()
                if source is None:
                    raise JudgeRunNotFoundError("Parecer fonte não encontrado.")
                if source["status"] != "succeeded" or source["report"] is None:
                    raise JudgeSourceUnavailableError(
                        "O judge exige um parecer concluído com sucesso."
                    )
                try:
                    source_report = EvaluationReport.model_validate(source["report"])
                except ValidationError as error:
                    raise JudgeSourceUnavailableError(
                        "O parecer fonte não atende ao contrato atual."
                    ) from error
                source_hash = report_sha256(source_report)
                source_json = json.dumps(source_report.model_dump(mode="json"))
                evidence_ids = sorted(
                    {
                        evidence_id
                        for dimension in source_report.dimensions
                        for evidence_id in dimension.evidence_ids
                    }
                )
                evidence_rows = []
                if evidence_ids:
                    evidence_rows = list(
                        connection.execute(
                            """
                            SELECT id, page, text
                            FROM document_units
                            WHERE document_id = %s AND id = ANY(%s)
                            ORDER BY page, id
                            """,
                            (source["document_id"], evidence_ids),
                        ).fetchall()
                    )
                if len(evidence_rows) != len(evidence_ids):
                    raise JudgeSourceUnavailableError(
                        "As evidências do parecer fonte não estão disponíveis."
                    )
                source_evidence = JudgeEvidencePackage(
                    document_id=source["document_id"],
                    revision_sha256=source_report.revision_sha256,
                    source_report_sha256=source_hash,
                    items=tuple(
                        JudgeEvidenceItem(
                            unit_id=row["id"],
                            page=row["page"],
                            text=row["text"],
                        )
                        for row in evidence_rows
                    ),
                )
                source_evidence.validate_source(source_report, source_hash)
                source_evidence_json = json.dumps(
                    source_evidence.model_dump(mode="json")
                )
                row = connection.execute(
                    """
                    INSERT INTO judge_runs (
                        id, source_run_id, document_id, idempotency_key, mode, provider,
                        model, prompt_version, status, source_report_sha256, source_report,
                        source_evidence
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, 'queued', %s, %s::jsonb,
                        %s::jsonb
                    )
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING *
                    """,
                    (
                        judge_run_id,
                        parsed_source_id,
                        source["document_id"],
                        idempotency_key,
                        mode.value,
                        provider,
                        model,
                        prompt_version,
                        source_hash,
                        source_json,
                        source_evidence_json,
                    ),
                ).fetchone()
                if row is not None:
                    return self._judge_from_row(row)
                if idempotency_key is None:
                    raise JudgeRunRepositoryError("O banco não retornou o judge criado.")
                existing = connection.execute(
                    "SELECT * FROM judge_runs WHERE idempotency_key = %s",
                    (idempotency_key,),
                ).fetchone()
                if existing is None:
                    raise JudgeRunRepositoryError("O judge idempotente não foi localizado.")
                expected = (
                    parsed_source_id,
                    mode.value,
                    provider,
                    model,
                    prompt_version,
                    source_hash,
                )
                observed = tuple(
                    existing[field]
                    for field in (
                        "source_run_id",
                        "mode",
                        "provider",
                        "model",
                        "prompt_version",
                        "source_report_sha256",
                    )
                )
                if observed != expected:
                    raise JudgeRunConflictError(
                        "Idempotency-Key já foi usada com outra solicitação."
                    )
                return self._judge_from_row(existing)
        except (
            JudgeRunConflictError,
            JudgeRunNotFoundError,
            JudgeRunRepositoryError,
            JudgeSourceUnavailableError,
        ):
            raise
        except psycopg.Error as error:
            raise JudgeRunRepositoryError("A persistência do judge falhou.") from error

    def get(self, judge_run_id: str) -> StoredJudgeRun:
        parsed_id = self._parse_uuid(judge_run_id, "Judge não encontrado.")
        rows = self._fetch_all("SELECT * FROM judge_runs WHERE id = %s", (parsed_id,))
        if not rows:
            raise JudgeRunNotFoundError("Judge não encontrado.")
        return self._judge_from_row(rows[0])

    def list_judge_runs(
        self, source_run_id: str | None = None
    ) -> tuple[StoredJudgeRun, ...]:
        if source_run_id is None:
            rows = self._fetch_all(
                "SELECT * FROM judge_runs ORDER BY created_at DESC, id DESC LIMIT 100"
            )
        else:
            parsed_source_id = self._parse_uuid(
                source_run_id, "Parecer fonte não encontrado."
            )
            rows = self._fetch_all(
                """
                SELECT * FROM judge_runs
                WHERE source_run_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 100
                """,
                (parsed_source_id,),
            )
        return tuple(self._judge_from_row(row) for row in rows)

    def claim_next(self) -> StoredJudgeRun | None:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    UPDATE judge_runs
                    SET status = 'running', started_at = now()
                    WHERE id = (
                        SELECT id FROM judge_runs
                        WHERE status = 'queued'
                        ORDER BY created_at, id
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    RETURNING *
                    """
                ).fetchone()
                return self._judge_from_row(row) if row else None
        except psycopg.Error as error:
            raise JudgeRunRepositoryError(
                "Não foi possível reivindicar o próximo judge."
            ) from error

    def succeed(self, judge_run_id: UUID, execution: JudgeExecution) -> StoredJudgeRun:
        report_json = json.dumps(execution.report.model_dump(mode="json"))
        return self._finish(
            judge_run_id,
            """
            UPDATE judge_runs
            SET status = 'succeeded', usage_kind = %s, credential_slot = %s,
                input_tokens = %s, output_tokens = %s, report = %s::jsonb, result_markdown = %s,
                finished_at = now()
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
                judge_run_id,
            ),
        )

    def fail(
        self, judge_run_id: UUID, error_code: str, error_message: str
    ) -> StoredJudgeRun:
        return self._finish(
            judge_run_id,
            """
            UPDATE judge_runs
            SET status = 'failed', error_code = %s, error_message = %s, finished_at = now()
            WHERE id = %s AND status = 'running'
            RETURNING *
            """,
            (error_code, error_message, judge_run_id),
        )

    def interrupt_running(self) -> int:
        try:
            with psycopg.connect(self.database_url) as connection:
                cursor = connection.execute(
                    """
                    UPDATE judge_runs
                    SET status = 'interrupted', error_code = 'worker_interrupted',
                        error_message = 'O worker anterior foi interrompido.',
                        finished_at = now()
                    WHERE status = 'running'
                    """
                )
                return cursor.rowcount
        except psycopg.Error as error:
            raise JudgeRunRepositoryError(
                "Não foi possível reconciliar judges interrompidos."
            ) from error

    def _finish(
        self, judge_run_id: UUID, query: str, parameters: Sequence[object]
    ) -> StoredJudgeRun:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                row = connection.execute(query, parameters).fetchone()
                if row is None:
                    raise JudgeRunConflictError("O judge não está no estado running.")
                return self._judge_from_row(row)
        except JudgeRunConflictError:
            raise
        except psycopg.Error as error:
            raise JudgeRunRepositoryError("Não foi possível concluir o judge.") from error

    def _fetch_all(
        self, query: str, parameters: Sequence[object] | None = None
    ) -> list[dict[str, Any]]:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                return list(connection.execute(query, parameters or ()).fetchall())
        except psycopg.Error as error:
            raise JudgeRunRepositoryError("A consulta de judges falhou.") from error

    @staticmethod
    def _parse_uuid(value: str, message: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as error:
            raise JudgeRunNotFoundError(message) from error

    @staticmethod
    def _judge_from_row(row: dict[str, Any]) -> StoredJudgeRun:
        source_report = row["source_report"]
        source_evidence = row["source_evidence"]
        report = row["report"]
        if isinstance(source_report, str):
            source_report = json.loads(source_report)
        if isinstance(report, str):
            report = json.loads(report)
        if isinstance(source_evidence, str):
            source_evidence = json.loads(source_evidence)
        return StoredJudgeRun(
            id=row["id"],
            source_run_id=row["source_run_id"],
            document_id=row["document_id"],
            mode=row["mode"],
            provider=row["provider"],
            model=row["model"],
            prompt_version=row["prompt_version"],
            status=RunStatus(row["status"]),
            source_report_sha256=row["source_report_sha256"],
            source_report=source_report,
            source_evidence=source_evidence,
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
