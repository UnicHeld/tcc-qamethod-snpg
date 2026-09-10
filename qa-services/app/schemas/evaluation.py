from enum import StrEnum

from pydantic import BaseModel, Field


class EvaluationMode(StrEnum):
    DEMO = "demo"
    REAL = "real"


class UsageKind(StrEnum):
    SIMULATED = "simulated"
    ACTUAL = "actual"
    UNKNOWN = "unknown"


class DocumentMetadata(BaseModel):
    file_name: str
    sha256: str
    page_count: int = Field(ge=1)
    character_count: int = Field(ge=1)


class ModelUsage(BaseModel):
    kind: UsageKind
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class EvaluationResponse(BaseModel):
    mode: EvaluationMode
    simulated: bool
    mode_label: str
    provider: str
    model: str
    prompt_version: str
    document: DocumentMetadata
    result_markdown: str = Field(min_length=1)
    usage: ModelUsage


class Capability(BaseModel):
    mode: EvaluationMode
    label: str
    available: bool
    reason: str | None = None
    provider: str
    model: str
    requires_external_confirmation: bool


class CapabilitiesResponse(BaseModel):
    default_mode: EvaluationMode
    max_upload_bytes: int = Field(gt=0)
    max_pages: int = Field(gt=0)
    capabilities: list[Capability]
