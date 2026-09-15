import asyncio
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import ValidationError

from app.adapters.postgres_runs import PostgresRunRepository
from app.core.config import Settings, get_settings
from app.domain.evaluation import EvaluationReport
from app.domain.runs import RunStatus, StoredRun
from app.schemas.evaluation import EvaluationMode
from app.schemas.runs import (
    RunCreateRequest,
    RunListResponse,
    RunResponse,
    RunResultResponse,
)
from app.services.evaluation_service import (
    PROMPT_VERSION,
    ProviderError,
    create_evaluation_adapter,
)
from app.services.run_service import (
    RunConflictError,
    RunNotFoundError,
    RunRepository,
    RunRepositoryError,
    RunService,
)

router = APIRouter()


def _api_error(status_code: int, code: str, message: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def get_run_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RunRepository:
    if not settings.database_url:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "database_unavailable",
            "A persistência PostgreSQL não está configurada.",
        )
    return PostgresRunRepository(settings.database_url)


def _run_response(run: StoredRun) -> RunResponse:
    return RunResponse.model_validate(run)


@router.post("", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    request: RunCreateRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[RunRepository, Depends(get_run_repository)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> RunResponse:
    if request.mode is EvaluationMode.REAL and not request.confirm_external_processing:
        _api_error(
            status.HTTP_400_BAD_REQUEST,
            "external_processing_not_confirmed",
            "Confirme o envio do texto extraído ao provedor externo.",
        )
    try:
        adapter = create_evaluation_adapter(request.mode, settings)
    except ProviderError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "provider_unavailable", str(error))

    service = RunService(repository)
    try:
        run = await asyncio.to_thread(
            service.create,
            str(request.document_id),
            request.mode,
            adapter.provider,
            adapter.model,
            PROMPT_VERSION,
            idempotency_key,
        )
    except RunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "document_not_found", str(error))
    except RunConflictError as error:
        _api_error(status.HTTP_409_CONFLICT, "idempotency_conflict", str(error))
    except RunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return _run_response(run)


@router.get("", response_model=RunListResponse)
async def list_runs(
    repository: Annotated[RunRepository, Depends(get_run_repository)],
    document_id: UUID | None = None,
) -> RunListResponse:
    try:
        runs = await asyncio.to_thread(
            repository.list_runs,
            str(document_id) if document_id else None,
        )
    except RunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "document_not_found", str(error))
    except RunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return RunListResponse(runs=tuple(_run_response(run) for run in runs))


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    repository: Annotated[RunRepository, Depends(get_run_repository)],
) -> RunResponse:
    try:
        run = await asyncio.to_thread(repository.get, run_id)
    except RunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "run_not_found", str(error))
    except RunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return _run_response(run)


@router.get("/{run_id}/result", response_model=RunResultResponse)
async def get_run_result(
    run_id: str,
    repository: Annotated[RunRepository, Depends(get_run_repository)],
) -> RunResultResponse:
    try:
        run = await asyncio.to_thread(repository.get, run_id)
    except RunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "run_not_found", str(error))
    except RunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))

    if run.status is not RunStatus.SUCCEEDED:
        _api_error(
            status.HTTP_409_CONFLICT,
            "run_result_unavailable",
            "O resultado só fica disponível após o run ser concluído com sucesso.",
        )
    try:
        report = EvaluationReport.model_validate(run.report)
    except ValidationError:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "stored_result_invalid",
            "O resultado persistido não atende ao contrato atual.",
        )
    if not run.result_markdown:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "stored_result_invalid",
            "O resultado persistido está incompleto.",
        )
    return RunResultResponse(
        run_id=run.id,
        report=report,
        result_markdown=run.result_markdown,
    )
