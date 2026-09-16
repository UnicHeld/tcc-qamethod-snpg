import asyncio
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import ValidationError

from app.adapters.postgres_insights import PostgresInsightRunRepository
from app.core.config import Settings, get_settings
from app.domain.insights import EvidencePackage, InsightReport, StoredInsightRun
from app.domain.runs import RunStatus
from app.schemas.evaluation import EvaluationMode
from app.schemas.insights import (
    InsightCreateRequest,
    InsightResultResponse,
    InsightRunListResponse,
    InsightRunResponse,
)
from app.services.evaluation_service import ProviderError
from app.services.insight_run_service import (
    InsightRunConflictError,
    InsightRunNotFoundError,
    InsightRunRepository,
    InsightRunRepositoryError,
    InsightRunService,
)
from app.services.insight_service import INSIGHT_PROMPT_VERSION, create_insight_adapter

router = APIRouter()


def _api_error(status_code: int, code: str, message: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def get_insight_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> InsightRunRepository:
    if not settings.database_url:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "database_unavailable",
            "A persistência PostgreSQL não está configurada.",
        )
    return PostgresInsightRunRepository(settings.database_url)


def _insight_response(insight: StoredInsightRun) -> InsightRunResponse:
    return InsightRunResponse.model_validate(insight)


@router.post("", response_model=InsightRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_insight(
    request: InsightCreateRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[InsightRunRepository, Depends(get_insight_repository)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> InsightRunResponse:
    if request.mode is EvaluationMode.REAL and not request.confirm_external_processing:
        _api_error(
            status.HTTP_400_BAD_REQUEST,
            "external_processing_not_confirmed",
            "Confirme o envio da pergunta e das evidências ao provedor externo.",
        )
    if request.retrieval_mode == "vector" and not settings.vector_search_enabled:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "vector_search_unavailable",
            "A busca vetorial local não está habilitada.",
        )
    try:
        adapter = create_insight_adapter(request.mode, settings)
    except ProviderError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "provider_unavailable", str(error))

    try:
        insight = await asyncio.to_thread(
            InsightRunService(repository).create,
            str(request.document_id),
            request.question,
            request.retrieval_mode,
            request.retrieval_limit,
            request.mode,
            adapter.provider,
            adapter.model,
            INSIGHT_PROMPT_VERSION,
            idempotency_key,
        )
    except InsightRunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "document_not_found", str(error))
    except InsightRunConflictError as error:
        _api_error(status.HTTP_409_CONFLICT, "idempotency_conflict", str(error))
    except InsightRunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return _insight_response(insight)


@router.get("", response_model=InsightRunListResponse)
async def list_insights(
    repository: Annotated[InsightRunRepository, Depends(get_insight_repository)],
    document_id: UUID | None = None,
) -> InsightRunListResponse:
    try:
        insights = await asyncio.to_thread(
            repository.list_insights,
            str(document_id) if document_id else None,
        )
    except InsightRunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "document_not_found", str(error))
    except InsightRunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return InsightRunListResponse(
        insights=tuple(_insight_response(insight) for insight in insights)
    )


@router.get("/{insight_id}", response_model=InsightRunResponse)
async def get_insight(
    insight_id: str,
    repository: Annotated[InsightRunRepository, Depends(get_insight_repository)],
) -> InsightRunResponse:
    try:
        insight = await asyncio.to_thread(repository.get, insight_id)
    except InsightRunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "insight_not_found", str(error))
    except InsightRunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return _insight_response(insight)


@router.get("/{insight_id}/result", response_model=InsightResultResponse)
async def get_insight_result(
    insight_id: str,
    repository: Annotated[InsightRunRepository, Depends(get_insight_repository)],
) -> InsightResultResponse:
    try:
        insight = await asyncio.to_thread(repository.get, insight_id)
    except InsightRunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "insight_not_found", str(error))
    except InsightRunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))

    if insight.status is not RunStatus.SUCCEEDED:
        _api_error(
            status.HTTP_409_CONFLICT,
            "insight_result_unavailable",
            "O resultado só fica disponível após o insight ser concluído com sucesso.",
        )
    try:
        package = EvidencePackage.model_validate(insight.evidence_package)
        report = InsightReport.model_validate(insight.report)
        report.validate_evidence(package)
    except (ValidationError, ValueError):
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "stored_result_invalid",
            "O resultado persistido não atende ao contrato atual.",
        )
    if not insight.result_markdown:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "stored_result_invalid",
            "O resultado persistido está incompleto.",
        )
    return InsightResultResponse(
        insight_id=insight.id,
        evidence_package=package,
        report=report,
        result_markdown=insight.result_markdown,
    )
