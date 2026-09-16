import asyncio

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.domain.evaluation import Dimension, DimensionResult, EvaluationDraft
from app.main import app
from app.routers import evaluation as evaluation_router
from app.schemas.evaluation import EvaluationMode, UsageKind
from app.services.evaluation_service import (
    GenerationResult,
    ProviderError,
    ProviderModelUnavailableError,
    ProviderQuotaExceededError,
)
from tests.pdf_factory import blank_pdf, synthetic_pdf


def setup_function() -> None:
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def teardown_function() -> None:
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def test_health_and_capabilities_boot_without_credentials(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with TestClient(app) as client:
        health_response = client.get("/health")
        capabilities_response = client.get("/capabilities")

    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"
    capabilities = capabilities_response.json()
    assert capabilities["default_mode"] == "demo"
    assert capabilities["capabilities"][0]["available"] is True
    assert capabilities["capabilities"][1]["available"] is False
    assert "Configure" in capabilities["capabilities"][1]["reason"]
    assert capabilities["judge_capabilities"][0]["available"] is True
    assert capabilities["judge_capabilities"][1]["available"] is False
    assert "QA_JUDGE_GEMINI_MODEL" in capabilities["judge_capabilities"][1]["reason"]
    assert capabilities["retrieval_capabilities"][0]["mode"] == "lexical"
    assert capabilities["retrieval_capabilities"][1]["mode"] == "vector"
    assert capabilities["retrieval_capabilities"][1]["available"] is False


def test_demo_upload_returns_a_marked_deterministic_result() -> None:
    payload = synthetic_pdf()

    with TestClient(app) as client:
        first_response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", payload, "application/pdf")},
            data={"mode": "demo"},
        )
        second_response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", payload, "application/pdf")},
            data={"mode": "demo"},
        )

    assert first_response.status_code == 200
    assert first_response.json() == second_response.json()
    result = first_response.json()
    assert result["simulated"] is True
    assert result["mode_label"] == "Simulado — sem inferência LLM"
    assert result["usage"]["kind"] == "simulated"
    assert result["document"]["page_count"] == 1
    assert result["document"]["units"][0]["page"] == 1
    assert "text" not in result["document"]["units"][0]
    assert result["report"]["simulated"] is True
    assert len(result["report"]["dimensions"]) == 6
    assert all(item["evidence_ids"] for item in result["report"]["dimensions"])
    assert result["result_markdown"].count("## ") == 6
    assert "Nota final" not in result["result_markdown"]


def test_invalid_structured_result_is_not_published_as_success(monkeypatch) -> None:
    class InvalidEvidenceAdapter:
        provider = "test-provider"
        model = "test-model"
        simulated = True
        mode_label = "Simulado"

        async def generate(self, document):
            draft = EvaluationDraft(
                title="Parecer inválido",
                summary="A estrutura é válida, mas a evidência não pertence à revisão.",
                dimensions=tuple(
                    DimensionResult(
                        dimension=dimension,
                        insufficient=False,
                        score=5.0,
                        justification="Justificativa de teste.",
                        evidence_ids=(f"{document.sha256}:page:999",),
                    )
                    for dimension in Dimension
                ),
            )
            return GenerationResult(draft=draft, usage_kind=UsageKind.SIMULATED)

    monkeypatch.setattr(
        evaluation_router,
        "create_evaluation_adapter",
        lambda mode, settings: InvalidEvidenceAdapter(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", synthetic_pdf(), "application/pdf")},
            data={"mode": "demo"},
        )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "provider_error"


def test_rejects_non_pdf_media_type() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.txt", b"texto", "text/plain")},
        )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_media_type"


def test_rejects_empty_file() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", b"", "application/pdf")},
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "empty_file"


def test_rejects_invalid_pdf_bytes() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", b"not a pdf", "application/pdf")},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_pdf"


def test_reports_pdf_without_text_as_ocr_requirement() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("scan.pdf", blank_pdf(), "application/pdf")},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "pdf_without_text"
    assert "OCR" in response.json()["detail"]["message"]


def test_real_mode_requires_confirmation_before_processing() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", synthetic_pdf(), "application/pdf")},
            data={"mode": "real", "confirm_external_processing": "false"},
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "external_processing_not_confirmed"


def test_real_mode_without_key_does_not_fall_back_to_demo(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", synthetic_pdf(), "application/pdf")},
            data={"mode": "real", "confirm_external_processing": "true"},
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "provider_unavailable"


def test_rejects_file_over_configured_limit() -> None:
    settings = evaluation_router.Settings(max_upload_bytes=8)
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", b"%PDF-1.4 oversized", "application/pdf")},
        )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "file_too_large"


def test_rejects_pdf_over_configured_page_limit() -> None:
    settings = evaluation_router.Settings(max_pages=1)
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", blank_pdf(page_count=2), "application/pdf")},
        )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "page_limit_exceeded"


def test_provider_error_is_not_published_as_success(monkeypatch) -> None:
    class FailingAdapter:
        provider = "test-provider"
        model = "test-model"
        simulated = False
        mode_label = "Real"

        async def generate(self, document):
            raise ProviderError("Falha controlada do provedor.")

    settings = evaluation_router.Settings(google_api_key="test-key")
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(
        evaluation_router,
        "create_evaluation_adapter",
        lambda mode, current_settings: FailingAdapter(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", synthetic_pdf(), "application/pdf")},
            data={"mode": EvaluationMode.REAL, "confirm_external_processing": "true"},
        )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "provider_error"


def test_unavailable_provider_model_is_reported_explicitly(monkeypatch) -> None:
    class MissingModelAdapter:
        provider = "test-provider"
        model = "missing-model"
        simulated = False
        mode_label = "Real"

        async def generate(self, document):
            raise ProviderModelUnavailableError(
                "O modelo missing-model não está disponível para esta chave/API."
            )

    settings = evaluation_router.Settings(google_api_key="test-key")
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(
        evaluation_router,
        "create_evaluation_adapter",
        lambda mode, current_settings: MissingModelAdapter(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", synthetic_pdf(), "application/pdf")},
            data={"mode": EvaluationMode.REAL, "confirm_external_processing": "true"},
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "provider_model_unavailable"


def test_reports_parse_timeout(monkeypatch) -> None:
    async def slow_to_thread(function, *args):
        await asyncio.sleep(0.02)
        return function(*args)

    settings = evaluation_router.Settings(parse_timeout_seconds=0.001)
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(evaluation_router.asyncio, "to_thread", slow_to_thread)

    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", synthetic_pdf(), "application/pdf")},
        )

    assert response.status_code == 504
    assert response.json()["detail"]["code"] == "parse_timeout"


def test_reports_provider_timeout(monkeypatch) -> None:
    class SlowAdapter:
        provider = "test-provider"
        model = "test-model"
        simulated = False
        mode_label = "Real"

        async def generate(self, document):
            await asyncio.sleep(0.02)

    settings = evaluation_router.Settings(
        google_api_key="test-key",
        llm_timeout_seconds=0.001,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(
        evaluation_router,
        "create_evaluation_adapter",
        lambda mode, current_settings: SlowAdapter(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", synthetic_pdf(), "application/pdf")},
            data={"mode": EvaluationMode.REAL, "confirm_external_processing": "true"},
        )

    assert response.status_code == 504
    assert response.json()["detail"]["code"] == "provider_timeout"


def test_reports_provider_quota_exceeded(monkeypatch) -> None:
    class QuotaExceededAdapter:
        provider = "test-provider"
        model = "test-model"
        simulated = False
        mode_label = "Real"

        async def generate(self, document):
            raise ProviderQuotaExceededError("Quota de teste indisponível.")

    settings = evaluation_router.Settings(google_api_key="test-key")
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(
        evaluation_router,
        "create_evaluation_adapter",
        lambda mode, current_settings: QuotaExceededAdapter(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/evaluation/upload",
            files={"file": ("fixture.pdf", synthetic_pdf(), "application/pdf")},
            data={"mode": EvaluationMode.REAL, "confirm_external_processing": "true"},
        )

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "provider_quota_exceeded"
