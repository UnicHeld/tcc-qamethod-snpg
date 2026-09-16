import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.domain.evaluation import Dimension, DimensionResult, EvaluationReport
from app.domain.judges import (
    FindingSeverity,
    JudgeCriterion,
    JudgeDraft,
    JudgeEvidenceItem,
    JudgeEvidencePackage,
    JudgeFinding,
    JudgeVerdict,
)
from app.schemas.evaluation import CredentialSlot, EvaluationMode, UsageKind
from app.services.evaluation_service import ProviderError
from app.services.judge_service import (
    GeminiJudgeAdapter,
    create_judge_adapter,
    finalize_judge,
    report_sha256,
)


def source_material() -> tuple[EvaluationReport, JudgeEvidencePackage]:
    revision = "e" * 64
    evidence_id = f"{revision}:page:1"
    report = EvaluationReport(
        revision_sha256=revision,
        simulated=False,
        title="Parecer avaliado",
        summary="Resumo do parecer.",
        dimensions=tuple(
            DimensionResult(
                dimension=dimension,
                insufficient=False,
                score=7.0,
                justification="Justificativa do avaliador.",
                evidence_ids=(evidence_id,),
            )
            for dimension in Dimension
        ),
    )
    evidence = JudgeEvidencePackage(
        document_id=uuid4(),
        revision_sha256=revision,
        source_report_sha256=report_sha256(report),
        items=(
            JudgeEvidenceItem(
                unit_id=evidence_id,
                page=1,
                text="A metodologia combinou entrevistas e análise documental.",
            ),
        ),
    )
    return report, evidence


def judge_draft(evidence_id: str) -> JudgeDraft:
    return JudgeDraft(
        verdict=JudgeVerdict.NEEDS_HUMAN_REVIEW,
        summary="Foi encontrada uma limitação de fundamentação.",
        findings=(
            JudgeFinding(
                id="J1",
                criterion=JudgeCriterion.EVIDENCE_ALIGNMENT,
                severity=FindingSeverity.WARNING,
                dimension=Dimension.ORIGINALITY,
                explanation="O trecho não demonstra contribuição original.",
                evidence_ids=(evidence_id,),
            ),
        ),
    )


def test_gemini_judge_receives_frozen_report_and_evidence() -> None:
    source, evidence = source_material()
    draft = judge_draft(evidence.items[0].unit_id)

    class FakeModels:
        def __init__(self) -> None:
            self.arguments: dict[str, object] = {}

        def generate_content(self, **kwargs: object) -> object:
            self.arguments = kwargs
            return SimpleNamespace(
                text=draft.model_dump_json(),
                usage_metadata=SimpleNamespace(
                    prompt_token_count=321,
                    candidates_token_count=54,
                ),
            )

    models = FakeModels()
    adapter = GeminiJudgeAdapter(
        api_key="test-key",
        model="judge-model",
        client_factory=lambda api_key: SimpleNamespace(models=models),
    )

    generation = asyncio.run(adapter.generate(source, evidence))
    execution = finalize_judge(uuid4(), source, evidence, adapter, generation)

    assert generation.usage_kind is UsageKind.ACTUAL
    assert generation.credential_slot is CredentialSlot.PRIMARY
    assert execution.report.simulated is False
    assert execution.report.findings[0].evidence_ids == (evidence.items[0].unit_id,)
    assert evidence.items[0].text in str(models.arguments["contents"])
    assert source.title in str(models.arguments["contents"])
    assert "Contribuição nova e diferença em relação ao estado da arte." in str(
        models.arguments["contents"]
    )
    assert "Não há nota final agregada." in str(models.arguments["contents"])
    config = models.arguments["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema


def test_real_judge_factory_requires_distinct_allowed_model() -> None:
    with pytest.raises(ProviderError, match="diferente"):
        create_judge_adapter(
            EvaluationMode.REAL,
            Settings(
                gemini_model="same-model",
                gemini_judge_model="same-model",
                allowed_gemini_models=("same-model",),
                google_api_key="test-key",
            ),
        )

    adapter = create_judge_adapter(
        EvaluationMode.REAL,
        Settings(
            gemini_model="generator-model",
            gemini_judge_model="judge-model",
            allowed_gemini_models=("generator-model", "judge-model"),
            google_api_key="test-key",
        ),
    )

    assert isinstance(adapter, GeminiJudgeAdapter)
    assert adapter.model == "judge-model"


def test_gemini_judge_uses_fallback_only_after_quota() -> None:
    source, evidence = source_material()
    draft = judge_draft(evidence.items[0].unit_id)
    requested_keys: list[str] = []

    class QuotaError(Exception):
        code = 429

    def client_factory(api_key: str):
        requested_keys.append(api_key)

        def generate_content(**kwargs: object) -> object:
            if api_key == "primary-key":
                raise QuotaError
            return SimpleNamespace(text=draft.model_dump_json(), usage_metadata=None)

        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    adapter = GeminiJudgeAdapter(
        api_key="primary-key",
        fallback_api_key="fallback-key",
        model="judge-model",
        client_factory=client_factory,
    )

    generation = asyncio.run(adapter.generate(source, evidence))

    assert requested_keys == ["primary-key", "fallback-key"]
    assert generation.credential_slot is CredentialSlot.FALLBACK
