import asyncio
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.core.config import Settings, get_settings
from app.schemas.documents import (
    DocumentListResponse,
    DocumentPageResponse,
    DocumentPagesResponse,
    DocumentResponse,
    DocumentUnitResponse,
    DocumentUnitsResponse,
)
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentRepository,
    DocumentRepositoryError,
    DocumentService,
)
from app.services.parser_service import (
    InvalidPdfError,
    PageLimitExceededError,
    PdfWithoutTextError,
)

router = APIRouter()
READ_CHUNK_BYTES = 1024 * 1024


def _api_error(status_code: int, code: str, message: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def get_document_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentRepository:
    if not settings.database_url:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "database_unavailable",
            "A persistência PostgreSQL não está configurada.",
        )
    return PostgresDocumentRepository(settings.database_url)


async def _read_upload(file: UploadFile, max_upload_bytes: int) -> bytes:
    content = bytearray()
    while chunk := await file.read(READ_CHUNK_BYTES):
        content.extend(chunk)
        if len(content) > max_upload_bytes:
            _api_error(
                status.HTTP_413_CONTENT_TOO_LARGE,
                "file_too_large",
                f"O arquivo excede o limite de {max_upload_bytes} bytes.",
            )
    if not content:
        _api_error(status.HTTP_400_BAD_REQUEST, "empty_file", "O arquivo está vazio.")
    return bytes(content)


def _document_response(document: object) -> DocumentResponse:
    return DocumentResponse.model_validate(document)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    file: Annotated[UploadFile, File(description="PDF digital a persistir")],
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
) -> DocumentResponse:
    if file.content_type and file.content_type != "application/pdf":
        _api_error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "unsupported_media_type",
            "Apenas arquivos PDF são aceitos.",
        )

    content = await _read_upload(file, settings.max_upload_bytes)
    service = DocumentService(repository, max_pages=settings.max_pages)
    try:
        document = await asyncio.to_thread(service.admit, file.filename, content)
    except PageLimitExceededError as error:
        _api_error(status.HTTP_413_CONTENT_TOO_LARGE, "page_limit_exceeded", str(error))
    except PdfWithoutTextError as error:
        _api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, "pdf_without_text", str(error))
    except InvalidPdfError as error:
        _api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_pdf", str(error))
    except DocumentRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return _document_response(document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
) -> DocumentListResponse:
    try:
        documents = await asyncio.to_thread(repository.list_documents)
    except DocumentRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return DocumentListResponse(
        documents=tuple(_document_response(document) for document in documents)
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
) -> DocumentResponse:
    try:
        document = await asyncio.to_thread(repository.get, document_id)
    except DocumentNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "document_not_found", str(error))
    except DocumentRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return _document_response(document)


@router.get("/{document_id}/units", response_model=DocumentUnitsResponse)
async def list_document_units(
    document_id: str,
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
) -> DocumentUnitsResponse:
    try:
        units = await asyncio.to_thread(repository.list_units, document_id)
    except DocumentNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "document_not_found", str(error))
    except DocumentRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return DocumentUnitsResponse(
        units=tuple(DocumentUnitResponse.model_validate(unit) for unit in units)
    )


@router.get("/{document_id}/pages", response_model=DocumentPagesResponse)
async def list_document_pages(
    document_id: str,
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
) -> DocumentPagesResponse:
    try:
        pages = await asyncio.to_thread(repository.list_pages, document_id)
    except DocumentNotFoundError as error:
        _api_error(status.HTTP_404_NOT_FOUND, "document_not_found", str(error))
    except DocumentRepositoryError as error:
        _api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", str(error))
    return DocumentPagesResponse(
        pages=tuple(DocumentPageResponse.model_validate(page) for page in pages)
    )
