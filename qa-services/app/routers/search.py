import asyncio
from functools import lru_cache
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.fastembed_text import FastEmbedTextEmbedder
from app.adapters.postgres_search import PostgresSearchRepository
from app.core.config import Settings, get_settings
from app.domain.search import EmbeddingProfile
from app.schemas.search import SearchHitResponse, SearchRequest, SearchResponse
from app.services.document_service import DocumentNotFoundError, DocumentRepositoryError
from app.services.search_service import (
    InvalidSearchQueryError,
    SearchRepository,
    SearchService,
    VectorSearchUnavailableError,
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


@lru_cache(maxsize=4)
def _get_vector_embedder(
    profile: EmbeddingProfile, cache_dir: str | None
) -> FastEmbedTextEmbedder:
    return FastEmbedTextEmbedder(profile, cache_dir)


@router.post("", response_model=SearchResponse)
async def search_document(
    request: SearchRequest,
    repository: Annotated[SearchRepository, Depends(get_search_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchResponse:
    embedder = None
    if request.retrieval_mode == "vector":
        if not settings.vector_search_enabled:
            _api_error(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "vector_search_unavailable",
                "A busca vetorial local não está habilitada.",
            )
        embedder = _get_vector_embedder(
            EmbeddingProfile(
                model=settings.embedding_model,
                dimension=settings.embedding_dimension,
                chunk_version=settings.embedding_chunk_version,
                max_tokens=settings.embedding_max_tokens,
                overlap_tokens=settings.embedding_overlap_tokens,
            ),
            settings.embedding_cache_dir,
        )
    try:
        result = await asyncio.to_thread(
            SearchService(repository, embedder).search,
            str(request.document_id),
            request.query,
            request.limit,
            request.retrieval_mode,
        )
    except InvalidSearchQueryError as error:
        _api_error(status.HTTP_400_BAD_REQUEST, "invalid_search_query", str(error))
    except DocumentNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "document_not_found", str(error))
    except DocumentRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    except VectorSearchUnavailableError as error:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "vector_search_unavailable",
            str(error),
        )

    return SearchResponse(
        document_id=result.document_id,
        query=result.query,
        retrieval_mode=result.retrieval_mode,
        embedding_model=(
            result.embedding_profile.model if result.embedding_profile else None
        ),
        embedding_dimension=(
            result.embedding_profile.dimension if result.embedding_profile else None
        ),
        chunk_version=(
            result.embedding_profile.chunk_version if result.embedding_profile else None
        ),
        hits=tuple(SearchHitResponse.model_validate(hit) for hit in result.hits),
    )
