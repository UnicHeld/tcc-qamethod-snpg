from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.evaluation import EvaluationReport
from app.domain.judges import JudgeEvidencePackage, JudgeReport
from app.domain.runs import RunStatus
from app.schemas.evaluation import CredentialSlot, EvaluationMode, UsageKind


class JudgeRunCreateRequest(BaseModel):
    source_run_id: UUID
    mode: EvaluationMode = EvaluationMode.DEMO
    confirm_external_processing: bool = False


class JudgeRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_run_id: UUID
    document_id: UUID
    mode: EvaluationMode
    provider: str
    model: str
    prompt_version: str
    status: RunStatus
    source_report_sha256: str
    usage_kind: UsageKind | None
    credential_slot: CredentialSlot | None
    input_tokens: int | None
    output_tokens: int | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JudgeRunListResponse(BaseModel):
    judge_runs: tuple[JudgeRunResponse, ...]


class JudgeRunResultResponse(BaseModel):
    judge_run_id: UUID
    source_report: EvaluationReport
    source_evidence: JudgeEvidencePackage
    report: JudgeReport
    result_markdown: str
