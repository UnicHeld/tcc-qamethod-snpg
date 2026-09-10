import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv

DEFAULT_MAX_UPLOAD_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_PAGES = 300
DEFAULT_PARSE_TIMEOUT_SECONDS = 60
DEFAULT_LLM_TIMEOUT_SECONDS = 180
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
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
    allowed_gemini_models: tuple[str, ...] = (DEFAULT_GEMINI_MODEL,)
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    google_api_key: str | None = field(default=None, repr=False)

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
        allowed_gemini_models=allowed_models,
        cors_origins=_csv_from_env("QA_CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
        google_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
    )
