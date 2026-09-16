import asyncio
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import ValidationError

from app.adapters.postgres_judges import PostgresJudgeRunRepository
from app.core.config import Settings, get_settings
from app.domain.evaluation import EvaluationReport
from app.domain.judges import JudgeEvidencePackage, JudgeReport, StoredJudgeRun
from app.domain.runs import RunStatus
from app.schemas.evaluation import EvaluationMode
from app.schemas.judges import (
    JudgeRunCreateRequest,
    JudgeRunListResponse,
    JudgeRunResponse,
    JudgeRunResultResponse,
)
from app.services.judge_run_service import (
    JudgeRunConflictError,
    JudgeRunNotFoundError,
    JudgeRunRepository,
    JudgeRunRepositoryError,
    JudgeRunService,
    JudgeSourceUnavailableError,
)
from app.services.evaluation_service import ProviderError
from app.services.judge_service import (
    JUDGE_PROMPT_VERSION,
    create_judge_adapter,
    report_sha256,
)

router = APIRouter()


def _api_error(status_code: int, code: str, message: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def get_judge_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JudgeRunRepository:
    if not settings.database_url:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "database_unavailable",
            "A persistência PostgreSQL não está configurada.",
        )
    return PostgresJudgeRunRepository(settings.database_url)


def _judge_response(judge_run: StoredJudgeRun) -> JudgeRunResponse:
    return JudgeRunResponse.model_validate(judge_run)


@router.post("", response_model=JudgeRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_judge_run(
    request: JudgeRunCreateRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[JudgeRunRepository, Depends(get_judge_repository)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JudgeRunResponse:
    if request.mode is EvaluationMode.REAL and not request.confirm_external_processing:
        _api_error(
            status.HTTP_400_BAD_REQUEST,
            "external_processing_not_confirmed",
            "Confirme o envio do parecer e das evidências citadas ao provedor externo.",
        )
    try:
        adapter = create_judge_adapter(request.mode, settings)
    except ProviderError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "provider_unavailable", str(error))
    try:
        judge_run = await asyncio.to_thread(
            JudgeRunService(repository).create,
            str(request.source_run_id),
            request.mode,
            adapter.provider,
            adapter.model,
            JUDGE_PROMPT_VERSION,
            idempotency_key,
        )
    except JudgeRunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "source_run_not_found", str(error))
    except JudgeSourceUnavailableError as error:
        _api_error(status.HTTP_409_CONFLICT, "source_result_unavailable", str(error))
    except JudgeRunConflictError as error:
        _api_error(status.HTTP_409_CONFLICT, "idempotency_conflict", str(error))
    except JudgeRunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return _judge_response(judge_run)


@router.get("", response_model=JudgeRunListResponse)
async def list_judge_runs(
    repository: Annotated[JudgeRunRepository, Depends(get_judge_repository)],
    source_run_id: UUID | None = None,
) -> JudgeRunListResponse:
    try:
        judge_runs = await asyncio.to_thread(
            repository.list_judge_runs,
            str(source_run_id) if source_run_id else None,
        )
    except JudgeRunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "source_run_not_found", str(error))
    except JudgeRunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return JudgeRunListResponse(
        judge_runs=tuple(_judge_response(judge_run) for judge_run in judge_runs)
    )


@router.get("/{judge_run_id}", response_model=JudgeRunResponse)
async def get_judge_run(
    judge_run_id: str,
    repository: Annotated[JudgeRunRepository, Depends(get_judge_repository)],
) -> JudgeRunResponse:
    try:
        judge_run = await asyncio.to_thread(repository.get, judge_run_id)
    except JudgeRunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "judge_run_not_found", str(error))
    except JudgeRunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return _judge_response(judge_run)


@router.get("/{judge_run_id}/result", response_model=JudgeRunResultResponse)
async def get_judge_result(
    judge_run_id: str,
    repository: Annotated[JudgeRunRepository, Depends(get_judge_repository)],
) -> JudgeRunResultResponse:
    try:
        judge_run = await asyncio.to_thread(repository.get, judge_run_id)
    except JudgeRunNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "judge_run_not_found", str(error))
    except JudgeRunRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    if judge_run.status is not RunStatus.SUCCEEDED:
        _api_error(
            status.HTTP_409_CONFLICT,
            "judge_result_unavailable",
            "O resultado só fica disponível após o judge ser concluído com sucesso.",
        )
    try:
        source = EvaluationReport.model_validate(judge_run.source_report)
        evidence = JudgeEvidencePackage.model_validate(judge_run.source_evidence)
        report = JudgeReport.model_validate(judge_run.report)
        source_hash = report_sha256(source)
        if source_hash != judge_run.source_report_sha256:
            raise ValueError("Snapshot divergente.")
        evidence.validate_source(source, source_hash)
        report.validate_source(source, source_hash)
    except (ValidationError, ValueError):
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "stored_result_invalid",
            "O resultado persistido não atende ao contrato atual.",
        )
    if not judge_run.result_markdown:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "stored_result_invalid",
            "O resultado persistido está incompleto.",
        )
    return JudgeRunResultResponse(
        judge_run_id=judge_run.id,
        source_report=source,
        source_evidence=evidence,
        report=report,
        result_markdown=judge_run.result_markdown,
    )
