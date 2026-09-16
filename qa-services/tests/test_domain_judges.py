import asyncio
from uuid import uuid4

import pytest

from app.domain.evaluation import Dimension, DimensionResult, EvaluationReport
from app.domain.judges import (
    FindingSeverity,
    JudgeCriterion,
    JudgeEvidencePackage,
    JudgeFinding,
    JudgeReport,
    JudgeVerdict,
    render_judge_markdown,
)
from app.services.judge_service import report_sha256
from app.services.judge_service import DemoJudgeAdapter, finalize_judge


def source_report() -> EvaluationReport:
    revision = "a" * 64
    return EvaluationReport(
        revision_sha256=revision,
        simulated=True,
        title="Parecer fonte",
        summary="Resumo",
        dimensions=tuple(
            DimensionResult(
                dimension=dimension,
                insufficient=False,
                score=5.0,
                justification="Justificativa",
                evidence_ids=(f"{revision}:page:1",),
            )
            for dimension in Dimension
        ),
    )


def test_judge_validates_source_and_renders_separate_finding() -> None:
    source = source_report()
    source_hash = report_sha256(source)
    report = JudgeReport(
        source_run_id=uuid4(),
        source_report_sha256=source_hash,
        revision_sha256=source.revision_sha256,
        simulated=True,
        verdict=JudgeVerdict.NEEDS_HUMAN_REVIEW,
        summary="Revisão necessária.",
        findings=(
            JudgeFinding(
                id="J1",
                criterion=JudgeCriterion.EVIDENCE_ALIGNMENT,
                severity=FindingSeverity.WARNING,
                dimension=Dimension.ORIGINALITY,
                explanation="A sustentação precisa de revisão.",
                evidence_ids=source.dimensions[0].evidence_ids,
            ),
        ),
    )

    markdown = render_judge_markdown(report, source, source_hash)

    assert "J1 — originality" in markdown
    assert str(report.source_run_id) in markdown


def test_judge_rejects_evidence_outside_source_snapshot() -> None:
    source = source_report()
    report = JudgeReport(
        source_run_id=uuid4(),
        source_report_sha256=report_sha256(source),
        revision_sha256=source.revision_sha256,
        simulated=False,
        verdict=JudgeVerdict.NEEDS_HUMAN_REVIEW,
        summary="Achado inválido.",
        findings=(
            JudgeFinding(
                id="J1",
                criterion=JudgeCriterion.EVIDENCE_ALIGNMENT,
                severity=FindingSeverity.ERROR,
                dimension=Dimension.ORIGINALITY,
                explanation="Referência inválida.",
                evidence_ids=("unknown-unit",),
            ),
        ),
    )

    with pytest.raises(ValueError, match="evidência inexistente"):
        report.validate_source(source, report_sha256(source))


def test_demo_judge_accepts_source_with_all_dimensions_insufficient() -> None:
    revision = "d" * 64
    source = EvaluationReport(
        revision_sha256=revision,
        simulated=True,
        title="Parecer insuficiente",
        summary="Sem evidências suficientes.",
        dimensions=tuple(
            DimensionResult(
                dimension=dimension,
                insufficient=True,
                score=None,
                justification="Material insuficiente.",
            )
            for dimension in Dimension
        ),
    )
    adapter = DemoJudgeAdapter()
    evidence = JudgeEvidencePackage(
        document_id=uuid4(),
        revision_sha256=source.revision_sha256,
        source_report_sha256=report_sha256(source),
        items=(),
    )

    execution = finalize_judge(
        uuid4(),
        source,
        evidence,
        adapter,
        asyncio.run(adapter.generate(source, evidence)),
    )

    assert execution.report.findings[0].criterion is JudgeCriterion.RUBRIC_CONFORMANCE
    assert execution.report.findings[0].evidence_ids == ()
