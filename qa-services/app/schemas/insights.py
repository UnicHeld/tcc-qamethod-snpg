from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.insights import EvidencePackage, InsightReport
from app.domain.runs import RunStatus
from app.schemas.evaluation import CredentialSlot, EvaluationMode, UsageKind


class InsightCreateRequest(BaseModel):
    document_id: UUID
    question: str = Field(min_length=1, max_length=200)
    retrieval_mode: Literal["lexical", "vector"] = "lexical"
    retrieval_limit: int = Field(default=5, ge=1, le=10, strict=True)
    mode: EvaluationMode = EvaluationMode.DEMO
    confirm_external_processing: bool = False

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Informe uma pergunta não vazia.")
        return normalized


class InsightRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    question: str
    retrieval_mode: Literal["lexical", "vector"]
    retrieval_limit: int
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


class InsightRunListResponse(BaseModel):
    insights: tuple[InsightRunResponse, ...]


class InsightResultResponse(BaseModel):
    insight_id: UUID
    evidence_package: EvidencePackage
    report: InsightReport
    result_markdown: str
