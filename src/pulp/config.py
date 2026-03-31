from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pulp.models import ColumnsMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    llm_enabled_default: bool = False
    strict_llm: bool = False

    force_ocr: bool = False
    columns_mode: ColumnsMode = ColumnsMode.AUTO

    detect_sample_pages: int = 3
    scanned_chars_threshold: int = 50
    ocr_low_confidence_threshold: float = 80.0
