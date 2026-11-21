import asyncio
from collections.abc import Callable
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.adapters.postgres_catalog import PostgresCatalogRepository
from app.core.config import Settings, get_settings
from app.domain.catalog import AcademicMetadata, CatalogFilters
from app.schemas.catalog import (
    CatalogEntryResponse,
    CatalogEvidenceResponse,
    CatalogFiltersRequest,
    CatalogHitResponse,
    CatalogListRequest,
    CatalogListResponse,
    CatalogSearchRequest,
    CatalogSearchResponse,
    SaveCatalogEntryRequest,
)
from app.services.catalog_service import (
    CatalogEntryNotFoundError,
    CatalogRepository,
    CatalogRevisionConflictError,
)
from app.services.document_service import DocumentNotFoundError, DocumentRepositoryError
from app.services.search_service import SearchService

router = APIRouter()
T = TypeVar("T")


def get_catalog_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CatalogRepository:
    if not settings.database_url:
        raise HTTPException(
            503,
            detail={
                "code": "database_unavailable",
                "message": "A persistência PostgreSQL não está configurada.",
            },
        )
    return PostgresCatalogRepository(settings.database_url)


async def _execute(operation: Callable[..., T], *args: object) -> T:
    try:
        return await asyncio.to_thread(operation, *args)
    except (
        CatalogEntryNotFoundError,
        CatalogRevisionConflictError,
        DocumentNotFoundError,
        DocumentRepositoryError,
    ) as error:
        status_code, code = {
            CatalogEntryNotFoundError: (404, "catalog_entry_not_found"),
            CatalogRevisionConflictError: (409, "catalog_revision_conflict"),
            DocumentNotFoundError: (404, "document_not_found"),
            DocumentRepositoryError: (503, "database_unavailable"),
        }[type(error)]
        raise HTTPException(status_code, detail={"code": code, "message": str(error)}) from error


@router.put("/documents/{document_id}", response_model=CatalogEntryResponse)
async def save_catalog_entry(
    document_id: UUID,
    request: SaveCatalogEntryRequest,
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
) -> CatalogEntryResponse:
    entry = await _execute(
        repository.save,
        document_id,
        AcademicMetadata(**request.metadata.model_dump()),
        request.expected_revision,
    )
    return CatalogEntryResponse.model_validate(entry)


@router.get("/documents", response_model=CatalogListResponse)
async def list_catalog_entries(
    request: Annotated[CatalogListRequest, Query()],
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
) -> CatalogListResponse:
    filters = CatalogFilters(**request.model_dump(exclude={"limit", "offset"}))
    result = await _execute(repository.list_entries, filters, request.limit, request.offset)
    return CatalogListResponse(
        entries=tuple(CatalogEntryResponse.model_validate(entry) for entry in result.entries),
        total=result.total,
        limit=request.limit,
        offset=request.offset,
    )


@router.get("/documents/{document_id}", response_model=CatalogEntryResponse)
async def get_catalog_entry(
    document_id: UUID,
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
) -> CatalogEntryResponse:
    return CatalogEntryResponse.model_validate(await _execute(repository.get, document_id))


@router.post("/search", response_model=CatalogSearchResponse)
async def search_catalog(
    request: CatalogSearchRequest,
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
) -> CatalogSearchResponse:
    result = await _execute(
        repository.search,
        request.query,
        CatalogFilters(**request.filters.model_dump()),
        request.limit,
        request.offset,
    )
    return CatalogSearchResponse(
        query=request.query,
        filters=CatalogFiltersRequest.model_validate(request.filters),
        hits=tuple(
            CatalogHitResponse(
                entry=CatalogEntryResponse.model_validate(hit.entry),
                unit_id=hit.unit_id,
                page=hit.page,
                snippet=SearchService._snippet(hit.text, request.query),
                score=hit.score,
            )
            for hit in result.hits
        ),
        total_hits=result.total_hits,
        total_documents=result.total_documents,
        limit=request.limit,
        offset=request.offset,
    )


@router.get("/documents/{document_id}/evidence/{unit_id}", response_model=CatalogEvidenceResponse)
async def get_catalog_evidence(
    document_id: UUID,
    unit_id: Annotated[str, Path(min_length=1, max_length=160)],
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
) -> CatalogEvidenceResponse:
    return CatalogEvidenceResponse.model_validate(
        await _execute(repository.get_evidence, document_id, unit_id)
    )
