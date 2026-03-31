from __future__ import annotations

from enum import StrEnum
from importlib import metadata
from pathlib import Path

import typer

from pulp.clean import clean_extraction
from pulp.config import Settings
from pulp.detect import detect_pdf
from pulp.extract import extract_pdf
from pulp.models import ColumnsMode
from pulp.render import render_markdown
from pulp.structure import LLMStructuringError, structure_document

app = typer.Typer(add_completion=False, no_args_is_help=True)


class _ColumnsChoice(StrEnum):
    auto = "auto"
    off = "off"


def _version_callback(value: bool) -> None:
    if not value:
        return

    import pulp

    version = getattr(pulp, "__version__", None)
    if not version:
        try:
            version = metadata.version("pulp")
        except metadata.PackageNotFoundError:
            version = "unknown"
        pulp.__version__ = version

    typer.echo(version)
    raise typer.Exit()


def _list_subtract(list_a: list[str], list_b: list[str]) -> list[str]:
    remaining = list(list_a)
    for item in list_b:
        try:
            remaining.remove(item)
        except ValueError:
            continue
    return remaining


def _format_diff_summary(*, detection, extraction, cleaned, structured, llm_enabled: bool) -> str:
    clean_stage_warnings = _list_subtract(list(cleaned.warnings), list(extraction.warnings))
    structure_stage_warnings = _list_subtract(list(structured.warnings), list(cleaned.warnings))

    fell_back = llm_enabled and any("Using heuristic output." in w for w in structured.warnings)

    stats = cleaned.stats
    lines = [
        f"classification: {detection.meta.classification}",
        f"page_count: {detection.meta.page_count}",
        f"avg_chars_per_page: {detection.avg_chars_per_page:.1f}",
        f"clean.removed_page_number_lines: {stats.removed_page_number_lines}",
        f"clean.removed_header_footer_lines: {stats.removed_header_footer_lines}",
        f"clean.rejoined_hyphenations: {stats.rejoined_hyphenations}",
        f"clean.reassembled_paragraphs: {stats.reassembled_paragraphs}",
        f"clean.dropped_blank_pages: {stats.dropped_blank_pages}",
        "warnings.detect: 0",
        f"warnings.extract: {len(extraction.warnings)}",
        f"warnings.clean: {len(clean_stage_warnings)}",
        f"warnings.structure: {len(structure_stage_warnings)}",
        f"llm.enabled: {str(bool(llm_enabled)).lower()}",
        f"llm.fell_back: {str(bool(fell_back)).lower()}",
    ]
    return "\n".join(lines)


@app.command("pulp")
def pulp_command(
    input_pdf: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
    output: Path | None = typer.Option(
        None,
        "-o",
        "--output",
        dir_okay=False,
        help="Output Markdown path (default: <input>.md).",
    ),
    diff: bool = typer.Option(
        False,
        "--diff",
        help="Print a human-readable summary to stderr.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable detailed per-stage logging (metadata only).",
    ),
    llm: bool | None = typer.Option(
        None,
        "--llm/--no-llm",
        help="Enable/disable the optional LLM structuring stage (default: off).",
    ),
    strict_llm: bool = typer.Option(
        False,
        "--strict-llm",
        help="Treat LLM failures as a hard error (exit code 4).",
    ),
    force_ocr: bool = typer.Option(
        False,
        "--force-ocr",
        help="Force OCR even if the PDF appears to have a text layer.",
    ),
    columns: _ColumnsChoice = typer.Option(
        _ColumnsChoice.auto,
        "--columns",
        help="Multi-column reading heuristic mode.",
    ),
) -> None:
    """
    Orchestrates the Pulp pipeline:
    Detect -> Extract -> Clean -> (optional LLM Structure) -> Render.

    This command is intentionally thin; business logic lives in src/pulp/.
    """

    settings = Settings()

    # Apply CLI overrides in-memory (no side effects).
    effective_llm = settings.llm_enabled_default if llm is None else llm
    effective_strict_llm = bool(settings.strict_llm or strict_llm)
    effective_force_ocr = bool(settings.force_ocr or force_ocr)
    effective_columns_mode = ColumnsMode.AUTO if columns.value == "auto" else ColumnsMode.OFF

    settings.strict_llm = effective_strict_llm
    settings.force_ocr = effective_force_ocr
    settings.columns_mode = effective_columns_mode

    detection = detect_pdf(input_pdf, settings=settings)
    extraction = extract_pdf(input_pdf, detection, settings=settings)
    cleaned = clean_extraction(extraction, settings=settings)

    try:
        structured = structure_document(cleaned, settings=settings, llm_enabled=effective_llm)
    except LLMStructuringError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=4) from exc

    output_path = output or input_pdf.with_suffix(".md")
    render_markdown(structured, output_path=output_path)

    if diff:
        summary = _format_diff_summary(
            detection=detection,
            extraction=extraction,
            cleaned=cleaned,
            structured=structured,
            llm_enabled=effective_llm,
        )
        typer.echo(summary, err=True)

    if verbose:
        # Metadata-only: avoid printing document text.
        typer.echo(f"Wrote {output_path}", err=True)


if __name__ == "__main__":
    app()
