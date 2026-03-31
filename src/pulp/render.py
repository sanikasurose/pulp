from __future__ import annotations

from pathlib import Path

from pulp.models import CleaningResult, StructuredDoc


def render_markdown(doc: StructuredDoc, *, output_path: Path) -> None:
    """Write Markdown output to disk."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    markdown = (doc.markdown or "").replace("\r\n", "\n").replace("\r", "\n")
    if markdown and not markdown.endswith("\n"):
        markdown += "\n"

    output_path.write_text(markdown, encoding="utf-8")


def build_structured_doc(cleaned: CleaningResult) -> StructuredDoc:
    """Deterministically assemble cleaned pages into a single Markdown string."""
    parts: list[str] = []
    for page in cleaned.pages:
        text = (page.clean_text or "").strip()
        if text:
            parts.append(text)

    markdown = "\n\n".join(parts).strip()
    if markdown and not markdown.endswith("\n"):
        markdown += "\n"

    return StructuredDoc(meta=cleaned.meta, markdown=markdown, warnings=list(cleaned.warnings))
