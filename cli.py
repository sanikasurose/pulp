from __future__ import annotations

from enum import StrEnum
from importlib import metadata
from pathlib import Path

import typer

from pulp.config import Settings
from pulp.models import ColumnsMode

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

    This command is intentionally scaffold-only; business logic is implemented by subsequent agents.
    """

    settings = Settings()

    # Apply CLI overrides in-memory (no side effects).
    effective_llm = settings.llm_enabled_default if llm is None else llm
    effective_strict_llm = settings.strict_llm or strict_llm
    effective_force_ocr = settings.force_ocr or force_ocr
    effective_columns_mode = ColumnsMode.AUTO if columns.value == "auto" else ColumnsMode.OFF

    _ = (
        input_pdf,
        version,
        output,
        diff,
        verbose,
        effective_llm,
        effective_strict_llm,
        effective_force_ocr,
        effective_columns_mode,
    )

    raise NotImplementedError


if __name__ == "__main__":
    app()
