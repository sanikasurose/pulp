from __future__ import annotations

import os
from pathlib import Path

from pulp.config import Settings
from pulp.models import CleaningResult, StructuredDoc
from pulp.render import build_structured_doc


class LLMStructuringError(RuntimeError):
    pass


_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

try:
    from anthropic import Anthropic as _Anthropic  # type: ignore
except Exception:  # noqa: BLE001
    _Anthropic = None


def structure_document(
    cleaned: CleaningResult, *, settings: Settings, llm_enabled: bool
) -> StructuredDoc:
    """
    Optionally apply an LLM-powered structuring pass; fall back on heuristic output on failure.
    """
    heuristic = build_structured_doc(cleaned)

    if not llm_enabled:
        return heuristic

    if not settings.anthropic_api_key:
        msg = "LLM unavailable: ANTHROPIC_API_KEY is missing."
        if settings.strict_llm:
            raise LLMStructuringError(msg)
        heuristic.warnings.append(f"{msg} Using heuristic output.")
        return heuristic

    if _Anthropic is None:
        msg = "LLM unavailable: anthropic client is not importable."
        if settings.strict_llm:
            raise LLMStructuringError(msg)
        heuristic.warnings.append(f"{msg} Using heuristic output.")
        return heuristic

    heading_prompt = _load_prompt("heading_v1.txt")
    structure_prompt = _load_prompt("structure_v1.txt")
    system_prompt = f"{heading_prompt}\n\n{structure_prompt}".strip()

    user_text = _format_cleaned_for_llm(cleaned)

    model = os.getenv("PULP_ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

    try:
        client = _Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_text,
                }
            ],
        )
        markdown = _anthropic_response_text(response).strip()
        if markdown and not markdown.endswith("\n"):
            markdown += "\n"
        return StructuredDoc(meta=cleaned.meta, markdown=markdown, warnings=list(cleaned.warnings))
    except Exception as exc:  # noqa: BLE001
        msg = f"LLM structuring failed ({exc.__class__.__name__})."
        if settings.strict_llm:
            raise LLMStructuringError(msg) from exc
        heuristic.warnings.append(f"{msg} Using heuristic output.")
        return heuristic


def _load_prompt(filename: str) -> str:
    path = _PROMPTS_DIR / filename
    return path.read_text(encoding="utf-8")


def _format_cleaned_for_llm(cleaned: CleaningResult) -> str:
    parts: list[str] = []
    for page in cleaned.pages:
        text = (page.clean_text or "").strip()
        parts.append(f"--- Page {page.page_number} ---\n{text}".strip())
    return "\n\n".join(parts).strip()


def _anthropic_response_text(response: object) -> str:
    # Newer Anthropic SDKs: `response.content` is a list of content blocks.
    content = getattr(response, "content", None)
    if isinstance(content, list) and content:
        first = content[0]
        text = getattr(first, "text", None)
        if isinstance(text, str):
            return text
        if isinstance(first, dict) and isinstance(first.get("text"), str):
            return str(first["text"])

    # Some SDK shapes expose `.text`.
    text_attr = getattr(response, "text", None)
    if isinstance(text_attr, str):
        return text_attr

    raise ValueError("Anthropic response did not contain text content.")
