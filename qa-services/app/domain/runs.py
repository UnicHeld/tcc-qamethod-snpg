from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True, slots=True)
class StoredRun:
    id: UUID
    document_id: UUID
    mode: str
    provider: str
    model: str
    prompt_version: str
    status: RunStatus
    usage_kind: str | None
    credential_slot: str | None
    input_tokens: int | None
    output_tokens: int | None
    report: dict[str, Any] | None
    result_markdown: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
