import asyncio
from pathlib import Path
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.config import Settings, get_settings
from app.schemas.evaluation import (
    DocumentMetadata,
    EvaluationMode,
    EvaluationResponse,
    ModelUsage,
)
from app.services.evaluation_service import (
    PROMPT_VERSION,
    ProviderError,
    ProviderQuotaExceededError,
    create_evaluation_adapter,
)
from app.services.parser_service import (
    InvalidPdfError,
    PageLimitExceededError,
    ParserService,
    PdfWithoutTextError,
)

router = APIRouter()
READ_CHUNK_BYTES = 1024 * 1024


def _api_error(status_code: int, code: str, message: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


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


@router.post("/upload", response_model=EvaluationResponse)
async def upload_evaluation(
    file: Annotated[UploadFile, File(description="PDF digital a avaliar")],
    settings: Annotated[Settings, Depends(get_settings)],
    mode: Annotated[EvaluationMode, Form()] = EvaluationMode.DEMO,
    confirm_external_processing: Annotated[bool, Form()] = False,
) -> EvaluationResponse:
    """Extrai um PDF digital e executa avaliação simulada ou real autorizada."""
    if file.content_type and file.content_type != "application/pdf":
        _api_error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "unsupported_media_type",
            "Apenas arquivos PDF são aceitos.",
        )

    if mode is EvaluationMode.REAL and not confirm_external_processing:
        _api_error(
            status.HTTP_400_BAD_REQUEST,
            "external_processing_not_confirmed",
            "Confirme o envio do texto extraído ao provedor externo.",
        )

    if mode is EvaluationMode.REAL and settings.real_mode_unavailable_reason:
        _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "provider_unavailable",
            settings.real_mode_unavailable_reason,
        )

    pdf_content = await _read_upload(file, settings.max_upload_bytes)
    parser = ParserService(max_pages=settings.max_pages)
    try:
        async with asyncio.timeout(settings.parse_timeout_seconds):
            document = await asyncio.to_thread(parser.extract_text, pdf_content)
    except TimeoutError:
        _api_error(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "parse_timeout",
            "A extração excedeu o tempo limite configurado.",
        )
    except PageLimitExceededError as error:
        _api_error(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "page_limit_exceeded",
            str(error),
        )
    except PdfWithoutTextError as error:
        _api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "pdf_without_text",
            str(error),
        )
    except InvalidPdfError as error:
        _api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_pdf",
            str(error),
        )

    adapter = create_evaluation_adapter(mode, settings)
    try:
        async with asyncio.timeout(settings.llm_timeout_seconds):
            generation = await adapter.generate(document)
    except TimeoutError:
        _api_error(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "provider_timeout",
            "A avaliação excedeu o tempo limite configurado.",
        )
    except ProviderQuotaExceededError as error:
        _api_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "provider_quota_exceeded",
            str(error),
        )
    except ProviderError as error:
        _api_error(status.HTTP_502_BAD_GATEWAY, "provider_error", str(error))

    safe_file_name = Path(file.filename or "documento.pdf").name
    return EvaluationResponse(
        mode=mode,
        simulated=adapter.simulated,
        mode_label=adapter.mode_label,
        provider=adapter.provider,
        model=adapter.model,
        prompt_version=PROMPT_VERSION,
        document=DocumentMetadata(
            file_name=safe_file_name,
            sha256=document.sha256,
            page_count=document.page_count,
            character_count=len(document.text),
        ),
        result_markdown=generation.markdown,
        usage=ModelUsage(
            kind=generation.usage_kind,
            input_tokens=generation.input_tokens,
            output_tokens=generation.output_tokens,
        ),
    )
