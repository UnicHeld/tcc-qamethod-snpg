from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.evaluation import EvaluationReport
from app.domain.runs import RunStatus
from app.schemas.evaluation import CredentialSlot, EvaluationMode, UsageKind


class RunCreateRequest(BaseModel):
    document_id: UUID
    mode: EvaluationMode = EvaluationMode.DEMO
    confirm_external_processing: bool = False


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    mode: EvaluationMode
    provider: str
    model: str
    prompt_version: str
    status: RunStatus
    usage_kind: UsageKind | None
    credential_slot: CredentialSlot | None
    input_tokens: int | None
    output_tokens: int | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RunListResponse(BaseModel):
    runs: tuple[RunResponse, ...]


class RunResultResponse(BaseModel):
    run_id: UUID
    report: EvaluationReport
    result_markdown: str
