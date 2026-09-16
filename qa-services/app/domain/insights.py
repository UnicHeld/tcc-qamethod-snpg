from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from app.domain.evaluation import Contract
from app.domain.runs import RunStatus


class EvidenceItem(Contract):
    id: str = Field(pattern=r"^E[1-9][0-9]*$")
    unit_id: str = Field(min_length=1)
    page: int = Field(ge=1, strict=True)
    text: str = Field(min_length=1)
    score: float = Field(allow_inf_nan=False, strict=True)


class EvidencePackage(Contract):
    document_id: UUID
    revision_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    question: str = Field(min_length=1, max_length=200)
    retrieval_mode: Literal["lexical", "vector"]
    embedding_model: str | None = None
    embedding_dimension: int | None = Field(default=None, ge=1, strict=True)
    chunk_version: str | None = None
    items: tuple[EvidenceItem, ...] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_profile_and_items(self) -> Self:
        profile = (self.embedding_model, self.embedding_dimension, self.chunk_version)
        if self.retrieval_mode == "vector" and any(value is None for value in profile):
            raise ValueError("Pacote vetorial exige perfil completo de embedding.")
        if self.retrieval_mode == "lexical" and any(value is not None for value in profile):
            raise ValueError("Pacote lexical não deve declarar perfil de embedding.")
        expected_ids = tuple(f"E{index}" for index in range(1, len(self.items) + 1))
        if tuple(item.id for item in self.items) != expected_ids:
            raise ValueError("IDs de evidência devem ser sequenciais e ordenados.")
        return self


class InsightDraft(Contract):
    answer: str = Field(min_length=1)
    citation_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_citations(self) -> Self:
        if len(set(self.citation_ids)) != len(self.citation_ids):
            raise ValueError("Citações duplicadas.")
        return self


class InsightReport(Contract):
    revision_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    simulated: bool = Field(strict=True)
    question: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1)
    citation_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_citations(self) -> Self:
        if len(set(self.citation_ids)) != len(self.citation_ids):
            raise ValueError("Citações duplicadas.")
        return self

    def validate_evidence(self, package: EvidencePackage) -> None:
        if self.revision_sha256 != package.revision_sha256:
            raise ValueError("Insight de outra revisão.")
        if self.question != package.question:
            raise ValueError("Insight de outra pergunta.")
        known_ids = {item.id for item in package.items}
        if not set(self.citation_ids).issubset(known_ids):
            raise ValueError("O insight referencia evidência inexistente.")


def render_insight_markdown(report: InsightReport, package: EvidencePackage) -> str:
    report.validate_evidence(package)
    label = "Simulado — sem inferência LLM" if report.simulated else "Insight RAG"
    sections = [
        f"# Insight RAG\n\n**{label}**",
        f"## Pergunta\n\n{report.question}",
        f"## Resposta\n\n{report.answer}",
        "## Evidências",
    ]
    evidence_by_id = {item.id: item for item in package.items}
    for citation_id in report.citation_ids:
        item = evidence_by_id[citation_id]
        sections.append(
            f"### {citation_id} — página {item.page}\n\n{item.text}\n\n"
            f"Origem: `{item.unit_id}`."
        )
    sections.append(
        f"Recuperação: `{package.retrieval_mode}`; revisão: `{package.revision_sha256}`."
    )
    return "\n\n".join(sections) + "\n"


@dataclass(frozen=True, slots=True)
class StoredInsightRun:
    id: UUID
    document_id: UUID
    question: str
    retrieval_mode: str
    retrieval_limit: int
    mode: str
    provider: str
    model: str
    prompt_version: str
    status: RunStatus
    usage_kind: str | None
    credential_slot: str | None
    input_tokens: int | None
    output_tokens: int | None
    evidence_package: dict[str, Any] | None
    report: dict[str, Any] | None
    result_markdown: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
