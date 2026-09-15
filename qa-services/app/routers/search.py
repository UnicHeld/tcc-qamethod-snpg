import asyncio
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.postgres_search import PostgresSearchRepository
from app.core.config import Settings, get_settings
from app.schemas.search import SearchHitResponse, SearchRequest, SearchResponse
from app.services.document_service import DocumentNotFoundError, DocumentRepositoryError
from app.services.search_service import (
    InvalidSearchQueryError,
    SearchRepository,
    SearchService,
)

router = APIRouter()


def _api_error(status_code: int, code: str, message: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def get_search_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchRepository:
    if not settings.database_url:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "database_unavailable",
            "A persistência PostgreSQL não está configurada.",
        )
    return PostgresSearchRepository(settings.database_url)


@router.post("", response_model=SearchResponse)
async def search_document(
    request: SearchRequest,
    repository: Annotated[SearchRepository, Depends(get_search_repository)],
) -> SearchResponse:
    try:
        result = await asyncio.to_thread(
            SearchService(repository).search,
            str(request.document_id),
            request.query,
            request.limit,
        )
    except InvalidSearchQueryError as error:
        _api_error(status.HTTP_400_BAD_REQUEST, "invalid_search_query", str(error))
    except DocumentNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "document_not_found", str(error))
    except DocumentRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))

    return SearchResponse(
        document_id=result.document_id,
        query=result.query,
        hits=tuple(SearchHitResponse.model_validate(hit) for hit in result.hits),
    )
