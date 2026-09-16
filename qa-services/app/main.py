from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.routers import documents, evaluation, insights, judges, runs, search
from app.schemas.evaluation import (
    CapabilitiesResponse,
    Capability,
    EvaluationMode,
    RetrievalCapability,
)


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.project_name, version=settings.project_version)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )
    application.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])
    application.include_router(
        documents.router, prefix="/api/v1/documents", tags=["documents"]
    )
    application.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])
    application.include_router(search.router, prefix="/api/v1/search", tags=["search"])
    application.include_router(
        insights.router, prefix="/api/v1/insights", tags=["insights"]
    )
    application.include_router(
        judges.router, prefix="/api/v1/judge-runs", tags=["judge-runs"]
    )

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
            judge_capabilities=[
                Capability(
                    mode=EvaluationMode.DEMO,
                    label="Simulado — validação técnica sem inferência LLM",
                    available=True,
                    provider="local",
                    model="deterministic-judge-demo-v1",
                    requires_external_confirmation=False,
                ),
                Capability(
                    mode=EvaluationMode.REAL,
                    label="LLM as judge — inferência externa autorizada",
                    available=current_settings.judge_real_mode_unavailable_reason is None,
                    reason=current_settings.judge_real_mode_unavailable_reason,
                    provider="google-gemini",
                    model=current_settings.gemini_judge_model or "não configurado",
                    requires_external_confirmation=True,
                ),
            ],
            retrieval_capabilities=[
                RetrievalCapability(
                    mode="lexical",
                    label="Lexical — índice textual PostgreSQL",
                    available=current_settings.database_url is not None,
                    reason=(
                        None
                        if current_settings.database_url
                        else "Configure DATABASE_URL para pesquisar documentos persistidos."
                    ),
                    model="postgresql-portuguese-fts",
                ),
                RetrievalCapability(
                    mode="vector",
                    label="Vetorial — embedding local",
                    available=(
                        current_settings.database_url is not None
                        and current_settings.vector_search_enabled
                    ),
                    reason=(
                        None
                        if current_settings.database_url
                        and current_settings.vector_search_enabled
                        else "Ative o perfil vetorial local e configure o PostgreSQL com pgvector."
                    ),
                    model=current_settings.embedding_model,
                    dimension=current_settings.embedding_dimension,
                ),
            ],
        )

    @application.get("/")
    async def root() -> dict[str, str]:
        return {"message": "QA Services API is running!", "health": "/health"}

    return application


app = create_app()
