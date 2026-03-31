from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DocumentClassification(str, Enum):
    TEXT_LAYER = "TEXT_LAYER"
    SCANNED = "SCANNED"


class ColumnsMode(str, Enum):
    AUTO = "auto"
    OFF = "off"


class DocumentMeta(BaseModel):
    source_path: str
    page_count: int = Field(..., ge=1)
    file_size_bytes: int = Field(..., ge=0)
    classification: DocumentClassification
    language: str | None = None


class DetectionResult(BaseModel):
    meta: DocumentMeta
    sampled_pages: int = Field(..., ge=1)
    avg_chars_per_page: float = Field(..., ge=0)


class ExtractedPage(BaseModel):
    page_number: int = Field(..., ge=1)
    raw_text: str
    ocr_confidence: float | None = Field(default=None, ge=0, le=100)


class ExtractionResult(BaseModel):
    meta: DocumentMeta
    pages: list[ExtractedPage]
    warnings: list[str] = Field(default_factory=list)


class CleaningStats(BaseModel):
    removed_page_number_lines: int = Field(default=0, ge=0)
    removed_header_footer_lines: int = Field(default=0, ge=0)
    rejoined_hyphenations: int = Field(default=0, ge=0)
    reassembled_paragraphs: int = Field(default=0, ge=0)
    dropped_blank_pages: int = Field(default=0, ge=0)


class CleanedPage(BaseModel):
    page_number: int = Field(..., ge=1)
    clean_text: str
    warnings: list[str] = Field(default_factory=list)


class CleaningResult(BaseModel):
    meta: DocumentMeta
    pages: list[CleanedPage]
    stats: CleaningStats = Field(default_factory=CleaningStats)
    warnings: list[str] = Field(default_factory=list)


class StructuredDoc(BaseModel):
    meta: DocumentMeta
    markdown: str
    warnings: list[str] = Field(default_factory=list)

