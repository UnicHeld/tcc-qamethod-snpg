from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
        str_strip_whitespace=True,
    )


class DocumentUnit(Contract):
    id: str = Field(min_length=1)
    page: int = Field(ge=1, strict=True)
    text: str = Field(min_length=1)


class DocumentRevision(Contract):
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    page_count: int = Field(ge=1, strict=True)
    units: tuple[DocumentUnit, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_units(self) -> Self:
        pages = [unit.page for unit in self.units]
        if pages != sorted(set(pages)):
            raise ValueError("As páginas devem ser únicas e ordenadas.")
        for unit in self.units:
            if unit.page > self.page_count or unit.id != f"{self.sha256}:page:{unit.page}":
                raise ValueError("Unidade incompatível com a revisão ou página.")
        return self


class Dimension(StrEnum):
    ORIGINALITY = "originality"
    RELEVANCE = "relevance"
    METHODOLOGY = "methodology"
    WRITING = "writing"
    STRUCTURE = "structure"
    INTERDISCIPLINARITY = "interdisciplinarity"


DIMENSION_LABELS = {
    Dimension.ORIGINALITY: "Originalidade do trabalho",
    Dimension.RELEVANCE: "Relevância científica, tecnológica, cultural e social",
    Dimension.METHODOLOGY: "Metodologia utilizada",
    Dimension.WRITING: "Qualidade da redação",
    Dimension.STRUCTURE: "Estrutura e organização do texto",
    Dimension.INTERDISCIPLINARITY: "Interdisciplinaridade",
}


class DimensionResult(Contract):
    dimension: Dimension
    insufficient: bool = Field(strict=True)
    score: float | None = Field(default=None, ge=0, le=10, allow_inf_nan=False, strict=True)
    justification: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_assessment(self) -> Self:
        if self.insufficient != (self.score is None):
            raise ValueError("Insuficiência exige nota nula; avaliação exige nota.")
        if not self.insufficient and not self.evidence_ids:
            raise ValueError("Uma nota exige evidência identificada.")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Evidências duplicadas.")
        return self


class EvaluationDraft(Contract):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    dimensions: tuple[DimensionResult, ...] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def validate_dimensions(self) -> Self:
        if {item.dimension for item in self.dimensions} != set(Dimension):
            raise ValueError("O parecer exige exatamente as seis dimensões distintas.")
        return self


class EvaluationReport(Contract):
    revision_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    simulated: bool = Field(strict=True)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    dimensions: tuple[DimensionResult, ...] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def validate_dimensions(self) -> Self:
        if {item.dimension for item in self.dimensions} != set(Dimension):
            raise ValueError("O parecer exige exatamente as seis dimensões distintas.")
        return self

    def validate_evidence(self, document: DocumentRevision) -> None:
        if self.revision_sha256 != document.sha256:
            raise ValueError("Parecer de outra revisão.")
        known_ids = {unit.id for unit in document.units}
        for item in self.dimensions:
            if not set(item.evidence_ids).issubset(known_ids):
                raise ValueError("O parecer referencia evidência inexistente.")


def render_markdown(report: EvaluationReport, document: DocumentRevision) -> str:
    report.validate_evidence(document)
    label = "Simulado — sem inferência LLM" if report.simulated else "Avaliação"
    sections = [f"# {report.title}\n\n**{label}**\n\n{report.summary}"]
    by_dimension = {item.dimension: item for item in report.dimensions}
    for dimension in Dimension:
        item = by_dimension[dimension]
        score = "Insuficiência de evidências — sem nota"
        if item.score is not None:
            prefix = "Nota simulada" if report.simulated else "Nota"
            score = f"{prefix}: {item.score:.1f}"
        sections.append(f"## {DIMENSION_LABELS[dimension]}\n\n{item.justification}\n\n**{score}**")
        if item.evidence_ids:
            pages = [unit.page for unit in document.units if unit.id in item.evidence_ids]
            sections.append("Evidências: páginas " + ", ".join(map(str, pages)) + ".")
    return "\n\n".join(sections) + "\n"
