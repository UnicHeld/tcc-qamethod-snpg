from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.routers import evaluation
from app.schemas.evaluation import CapabilitiesResponse, Capability, EvaluationMode


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.project_name, version=settings.project_version)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.project_name}

    @application.get("/capabilities", response_model=CapabilitiesResponse)
    async def capabilities(
        current_settings: Settings = Depends(get_settings),
    ) -> CapabilitiesResponse:
        unavailable_reason = current_settings.real_mode_unavailable_reason
        default_mode = EvaluationMode(current_settings.default_evaluation_mode)
        if default_mode is EvaluationMode.REAL and unavailable_reason:
            default_mode = EvaluationMode.DEMO

        return CapabilitiesResponse(
            default_mode=default_mode,
            max_upload_bytes=current_settings.max_upload_bytes,
            max_pages=current_settings.max_pages,
            capabilities=[
                Capability(
                    mode=EvaluationMode.DEMO,
                    label="Simulado — sem inferência LLM",
                    available=True,
                    provider="local",
                    model="deterministic-demo-v1",
                    requires_external_confirmation=False,
                ),
                Capability(
                    mode=EvaluationMode.REAL,
                    label="Real — inferência externa autorizada",
                    available=unavailable_reason is None,
                    reason=unavailable_reason,
                    provider="google-gemini",
                    model=current_settings.gemini_model,
                    requires_external_confirmation=True,
                ),
            ],
        )

    @application.get("/")
    async def root() -> dict[str, str]:
        return {"message": "QA Services API is running!", "health": "/health"}

    return application


app = create_app()
