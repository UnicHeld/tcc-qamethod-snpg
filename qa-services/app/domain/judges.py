from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Self
from uuid import UUID

from pydantic import Field, model_validator

from app.domain.evaluation import Contract, Dimension, EvaluationReport
from app.domain.runs import RunStatus


class JudgeCriterion(StrEnum):
    EVIDENCE_ALIGNMENT = "evidence_alignment"
    INTERNAL_CONSISTENCY = "internal_consistency"
    RUBRIC_CONFORMANCE = "rubric_conformance"


class FindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class JudgeVerdict(StrEnum):
    PASS = "pass"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class JudgeEvidenceItem(Contract):
    unit_id: str = Field(min_length=1)
    page: int = Field(ge=1, strict=True)
    text: str = Field(min_length=1)


class JudgeEvidencePackage(Contract):
    document_id: UUID
    revision_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    items: tuple[JudgeEvidenceItem, ...] = Field(max_length=300)

    @model_validator(mode="after")
    def validate_items(self) -> Self:
        unit_ids = tuple(item.unit_id for item in self.items)
        if len(set(unit_ids)) != len(unit_ids):
            raise ValueError("O pacote do judge contém evidências duplicadas.")
        order = tuple((item.page, item.unit_id) for item in self.items)
        if order != tuple(sorted(order)):
            raise ValueError("As evidências do judge devem estar ordenadas.")
        return self

    def validate_source(self, source: EvaluationReport, source_sha256: str) -> None:
        if self.revision_sha256 != source.revision_sha256:
            raise ValueError("Pacote de evidências pertence a outra revisão.")
        if self.source_report_sha256 != source_sha256:
            raise ValueError("Pacote de evidências pertence a outro parecer.")
        expected_ids = {
            evidence_id
            for dimension in source.dimensions
            for evidence_id in dimension.evidence_ids
        }
        if {item.unit_id for item in self.items} != expected_ids:
            raise ValueError("O pacote não congela exatamente as evidências citadas.")


class JudgeFinding(Contract):
    id: str = Field(pattern=r"^J[1-9][0-9]*$")
    criterion: JudgeCriterion
    severity: FindingSeverity
    dimension: Dimension | None = None
    explanation: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_evidence_alignment(self) -> Self:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Evidências duplicadas no achado.")
        if self.criterion is JudgeCriterion.EVIDENCE_ALIGNMENT:
            if self.dimension is None or not self.evidence_ids:
                raise ValueError(
                    "Achado de fundamentação exige dimensão e evidência identificada."
                )
        return self


class JudgeDraft(Contract):
    verdict: JudgeVerdict
    summary: str = Field(min_length=1)
    findings: tuple[JudgeFinding, ...] = ()

    @model_validator(mode="after")
    def validate_verdict(self) -> Self:
        if self.verdict is JudgeVerdict.PASS and self.findings:
            raise ValueError("Parecer aprovado não deve conter achados.")
        expected_ids = tuple(f"J{index}" for index in range(1, len(self.findings) + 1))
        if tuple(finding.id for finding in self.findings) != expected_ids:
            raise ValueError("IDs de achados devem ser sequenciais e ordenados.")
        return self


class JudgeReport(Contract):
    source_run_id: UUID
    source_report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    revision_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    simulated: bool = Field(strict=True)
    verdict: JudgeVerdict
    summary: str = Field(min_length=1)
    findings: tuple[JudgeFinding, ...] = ()

    @model_validator(mode="after")
    def validate_verdict(self) -> Self:
        if self.verdict is JudgeVerdict.PASS and self.findings:
            raise ValueError("Parecer aprovado não deve conter achados.")
        expected_ids = tuple(f"J{index}" for index in range(1, len(self.findings) + 1))
        if tuple(finding.id for finding in self.findings) != expected_ids:
            raise ValueError("IDs de achados devem ser sequenciais e ordenados.")
        return self

    def validate_source(self, source: EvaluationReport, source_sha256: str) -> None:
        if self.source_report_sha256 != source_sha256:
            raise ValueError("Judge referencia outro snapshot de parecer.")
        if self.revision_sha256 != source.revision_sha256:
            raise ValueError("Judge referencia outra revisão documental.")

        dimensions = {item.dimension: item for item in source.dimensions}
        known_evidence = {
            evidence_id
            for item in source.dimensions
            for evidence_id in item.evidence_ids
        }
        for finding in self.findings:
            if not set(finding.evidence_ids).issubset(known_evidence):
                raise ValueError("O judge referencia evidência inexistente no parecer fonte.")
            if finding.dimension is not None:
                dimension_evidence = set(dimensions[finding.dimension].evidence_ids)
                if not set(finding.evidence_ids).issubset(dimension_evidence):
                    raise ValueError("O achado referencia evidência de outra dimensão.")


def render_judge_markdown(
    report: JudgeReport, source: EvaluationReport, source_sha256: str
) -> str:
    report.validate_source(source, source_sha256)
    label = "Simulado — sem inferência LLM" if report.simulated else "Judge"
    sections = [
        f"# Auditoria de parecer\n\n**{label}**",
        f"## Resultado\n\n{report.summary}\n\nVeredito: `{report.verdict.value}`.",
    ]
    if not report.findings:
        sections.append("## Achados\n\nNenhum achado foi registrado.")
    for finding in report.findings:
        dimension = f" — {finding.dimension.value}" if finding.dimension else ""
        sections.append(
            f"## {finding.id}{dimension}\n\n{finding.explanation}\n\n"
            f"Critério: `{finding.criterion.value}`; severidade: `{finding.severity.value}`."
        )
        if finding.evidence_ids:
            sections.append("Evidências do parecer: " + ", ".join(finding.evidence_ids) + ".")
    sections.append(
        f"Parecer fonte: `{report.source_run_id}`; snapshot: "
        f"`{report.source_report_sha256}`."
    )
    return "\n\n".join(sections) + "\n"


@dataclass(frozen=True, slots=True)
class StoredJudgeRun:
    id: UUID
    source_run_id: UUID
    document_id: UUID
    mode: str
    provider: str
    model: str
    prompt_version: str
    status: RunStatus
    source_report_sha256: str
    source_report: dict[str, Any]
    source_evidence: dict[str, Any]
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
