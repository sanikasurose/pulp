from __future__ import annotations

from pathlib import Path

from pulp.config import Settings
from pulp.models import CleanedPage, CleaningResult, StructuredDoc
from pulp.render import build_structured_doc


class LLMStructuringError(RuntimeError):
    pass


_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_LLM_CHUNK_MAX_TOKENS = 4000

try:
    from anthropic import Anthropic as _Anthropic  # type: ignore
except Exception:  # noqa: BLE001
    _Anthropic = None


def _llm_unavailable_fallback(msg: str, heuristic: StructuredDoc, *, strict: bool) -> StructuredDoc:
    """Raise LLMStructuringError when strict, otherwise append warning and return heuristic."""
    if strict:
        raise LLMStructuringError(msg)
    heuristic.warnings.append(f"{msg} Using heuristic output.")
    return heuristic


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
        return _llm_unavailable_fallback(
            "LLM unavailable: ANTHROPIC_API_KEY is missing.", heuristic, strict=settings.strict_llm
        )

    if _Anthropic is None:
        return _llm_unavailable_fallback(
            "LLM unavailable: anthropic client is not importable.",
            heuristic,
            strict=settings.strict_llm,
        )

    system_prompt = _load_prompt("structure_v1.txt").strip()

    model = settings.anthropic_model

    try:
        client = _Anthropic(api_key=settings.anthropic_api_key)

        chunks = _chunk_cleaned_pages(cleaned.pages, max_tokens=_LLM_CHUNK_MAX_TOKENS)
        if not chunks:
            return heuristic

        outputs: list[str] = []
        for chunk_pages in chunks:
            chunk_text = _format_pages_for_llm(chunk_pages)
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=0,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": chunk_text,
                    }
                ],
            )
            chunk_md = _anthropic_response_text(response).strip()
            if chunk_md:
                outputs.append(chunk_md)

        markdown = "\n\n".join(outputs).strip()
        if markdown and not markdown.endswith("\n"):
            markdown += "\n"

        return StructuredDoc(
            meta=cleaned.meta,
            markdown=markdown,
            warnings=list(cleaned.warnings),
        )
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
    return _format_pages_for_llm(cleaned.pages)


def _format_pages_for_llm(pages: list[CleanedPage]) -> str:
    parts: list[str] = []
    for page in pages:
        text = (page.clean_text or "").strip()
        parts.append(f"--- Page {page.page_number} ---\n{text}".strip())
    return "\n\n".join(parts).strip()


def _chunk_cleaned_pages(
    pages: list[CleanedPage],
    *,
    max_tokens: int,
) -> list[list[CleanedPage]]:
    chunks: list[list[CleanedPage]] = []
    current: list[CleanedPage] = []
    current_tokens = 0

    for page in pages:
        page_text = f"--- Page {page.page_number} ---\n{(page.clean_text or '').strip()}".strip()
        page_tokens = _estimate_tokens(page_text)

        if current and (current_tokens + page_tokens) > max_tokens:
            chunks.append(current)
            current = []
            current_tokens = 0

        current.append(page)
        current_tokens += page_tokens

    if current:
        chunks.append(current)
    return chunks


def _estimate_tokens(text: str) -> int:
    text = text or ""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:  # noqa: BLE001
        # Deterministic fallback: rough chars->tokens approximation.
        return max(1, len(text) // 4)


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
