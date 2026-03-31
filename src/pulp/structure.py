from __future__ import annotations

from pulp.config import Settings
from pulp.models import CleaningResult, StructuredDoc


def structure_document(cleaned: CleaningResult, *, settings: Settings, llm_enabled: bool) -> StructuredDoc:
    """Optionally apply an LLM-powered structuring pass; fall back to heuristic output on failure."""
    raise NotImplementedError

