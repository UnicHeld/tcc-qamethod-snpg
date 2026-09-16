from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.insights import (
    EvidenceItem,
    EvidencePackage,
    InsightReport,
    render_insight_markdown,
)


def evidence_package() -> EvidencePackage:
    return EvidencePackage(
        document_id=uuid4(),
        revision_sha256="a" * 64,
        question="Qual método foi utilizado?",
        retrieval_mode="lexical",
        items=(
            EvidenceItem(
                id="E1",
                unit_id=f"{'a' * 64}:page:2",
                page=2,
                text="Foram realizadas entrevistas semiestruturadas.",
                score=0.75,
            ),
        ),
    )


def test_report_validates_citations_and_renders_sources() -> None:
    package = evidence_package()
    report = InsightReport(
        revision_sha256=package.revision_sha256,
        simulated=False,
        question=package.question,
        answer="O estudo utilizou entrevistas semiestruturadas.",
        citation_ids=("E1",),
    )

    markdown = render_insight_markdown(report, package)

    assert "E1 — página 2" in markdown
    assert package.items[0].unit_id in markdown
    assert "O estudo utilizou entrevistas" in markdown


def test_report_rejects_citation_outside_frozen_package() -> None:
    package = evidence_package()
    report = InsightReport(
        revision_sha256=package.revision_sha256,
        simulated=False,
        question=package.question,
        answer="Resposta sem fonte válida.",
        citation_ids=("E2",),
    )

    with pytest.raises(ValueError, match="evidência inexistente"):
        report.validate_evidence(package)


def test_evidence_package_rejects_incomplete_vector_profile() -> None:
    with pytest.raises(ValidationError, match="perfil completo"):
        EvidencePackage(
            document_id=uuid4(),
            revision_sha256="a" * 64,
            question="Pergunta",
            retrieval_mode="vector",
            embedding_model="test/model",
            items=(
                EvidenceItem(
                    id="E1",
                    unit_id="unit-1",
                    page=1,
                    text="Trecho",
                    score=0.5,
                ),
            ),
        )
