import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv

DEFAULT_MAX_UPLOAD_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_PAGES = 300
DEFAULT_PARSE_TIMEOUT_SECONDS = 60
DEFAULT_LLM_TIMEOUT_SECONDS = 180
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_EMBEDDING_DIMENSION = 384
DEFAULT_EMBEDDING_CHUNK_VERSION = "document-unit-v1"
DEFAULT_EMBEDDING_MAX_TOKENS = 384
DEFAULT_EMBEDDING_OVERLAP_TOKENS = 64
DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


def _positive_int_from_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} deve ser um número inteiro.") from error

    if value <= 0:
        raise ValueError(f"{name} deve ser maior que zero.")
    return value


def _csv_from_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    values = tuple(item.strip() for item in raw_value.split(",") if item.strip())
    if not values:
        raise ValueError(f"{name} deve conter ao menos um valor.")
    return values


def _bool_from_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} deve ser verdadeiro ou falso.")


@dataclass(frozen=True, slots=True)
class Settings:
    project_name: str = "QA Method"
    project_version: str = "0.1.0"
    default_evaluation_mode: Literal["demo", "real"] = "demo"
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES
    max_pages: int = DEFAULT_MAX_PAGES
    parse_timeout_seconds: int = DEFAULT_PARSE_TIMEOUT_SECONDS
    llm_timeout_seconds: int = DEFAULT_LLM_TIMEOUT_SECONDS
    gemini_model: str = DEFAULT_GEMINI_MODEL
    vector_search_enabled: bool = False
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_dimension: int = DEFAULT_EMBEDDING_DIMENSION
    embedding_chunk_version: str = DEFAULT_EMBEDDING_CHUNK_VERSION
    embedding_max_tokens: int = DEFAULT_EMBEDDING_MAX_TOKENS
    embedding_overlap_tokens: int = DEFAULT_EMBEDDING_OVERLAP_TOKENS
    embedding_cache_dir: str | None = None
    allowed_gemini_models: tuple[str, ...] = (DEFAULT_GEMINI_MODEL,)
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    database_url: str | None = field(default=None, repr=False)
    google_api_key: str | None = field(default=None, repr=False)
    gemini_fallback_api_key: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.embedding_dimension != DEFAULT_EMBEDDING_DIMENSION:
            raise ValueError(
                f"QA_EMBEDDING_DIMENSION deve ser {DEFAULT_EMBEDDING_DIMENSION} no perfil atual."
            )
        if self.embedding_overlap_tokens >= self.embedding_max_tokens:
            raise ValueError(
                "QA_EMBEDDING_OVERLAP_TOKENS deve ser menor que QA_EMBEDDING_MAX_TOKENS."
            )
        if not self.embedding_chunk_version.strip():
            raise ValueError("QA_EMBEDDING_CHUNK_VERSION não pode ser vazia.")

    @property
    def real_mode_unavailable_reason(self) -> str | None:
        if self.gemini_model not in self.allowed_gemini_models:
            return "O modelo configurado não está na allowlist local."
        if not self.google_api_key:
            return "Configure GEMINI_API_KEY ou GOOGLE_API_KEY no backend."
        return None


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    default_mode = os.getenv("QA_DEFAULT_MODE", "demo").lower()
    if default_mode not in {"demo", "real"}:
        raise ValueError("QA_DEFAULT_MODE deve ser 'demo' ou 'real'.")

    gemini_model = os.getenv("QA_GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    allowed_models = _csv_from_env("QA_ALLOWED_GEMINI_MODELS", (DEFAULT_GEMINI_MODEL,))

    return Settings(
        default_evaluation_mode=default_mode,
        max_upload_bytes=_positive_int_from_env(
            "QA_MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES
        ),
        max_pages=_positive_int_from_env("QA_MAX_PAGES", DEFAULT_MAX_PAGES),
        parse_timeout_seconds=_positive_int_from_env(
            "QA_PARSE_TIMEOUT_SECONDS", DEFAULT_PARSE_TIMEOUT_SECONDS
        ),
        llm_timeout_seconds=_positive_int_from_env(
            "QA_LLM_TIMEOUT_SECONDS", DEFAULT_LLM_TIMEOUT_SECONDS
        ),
        gemini_model=gemini_model,
        vector_search_enabled=_bool_from_env("QA_VECTOR_SEARCH_ENABLED", False),
        embedding_model=os.getenv("QA_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        embedding_dimension=_positive_int_from_env(
            "QA_EMBEDDING_DIMENSION", DEFAULT_EMBEDDING_DIMENSION
        ),
        embedding_chunk_version=os.getenv(
            "QA_EMBEDDING_CHUNK_VERSION", DEFAULT_EMBEDDING_CHUNK_VERSION
        ),
        embedding_max_tokens=_positive_int_from_env(
            "QA_EMBEDDING_MAX_TOKENS", DEFAULT_EMBEDDING_MAX_TOKENS
        ),
        embedding_overlap_tokens=_positive_int_from_env(
            "QA_EMBEDDING_OVERLAP_TOKENS", DEFAULT_EMBEDDING_OVERLAP_TOKENS
        ),
        embedding_cache_dir=os.getenv("QA_EMBEDDING_CACHE_DIR"),
        allowed_gemini_models=allowed_models,
        cors_origins=_csv_from_env("QA_CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
        database_url=os.getenv("DATABASE_URL"),
        google_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        gemini_fallback_api_key=os.getenv("GEMINI_FALLBACK_API_KEY"),
    )
