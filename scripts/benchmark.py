from __future__ import annotations

import argparse
import json
import tempfile
import time
import warnings
from pathlib import Path
from typing import Any

import tiktoken

from pulp.clean import clean_extraction
from pulp.config import Settings
from pulp.detect import detect_pdf
from pulp.extract import extract_pdf
from pulp.render import render_markdown
from pulp.structure import LLMStructuringError, structure_document


def _human_bytes(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KiB"
    return f"{num_bytes / (1024 * 1024):.1f} MiB"


def _format_md_table(rows: list[dict[str, Any]]) -> str:
    headers = [
        "document",
        "classification",
        "page_count",
        "input_bytes",
        "input_tokens",
        "output_tokens",
        "warnings",
        "runtime_s",
    ]

    def fmt(v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    body = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        body.append("| " + " | ".join(fmt(row.get(h)) for h in headers) + " |")
    return "\n".join(body) + "\n"


def run_benchmark(
    *,
    fixtures_dir: Path,
    output_path: Path,
    json_output_path: Path | None,
    llm_enabled: bool,
    strict_llm: bool,
    force_ocr: bool,
) -> None:
    """Run the Pulp pipeline across fixture PDFs and write benchmark results."""
    fixtures_dir = Path(fixtures_dir)
    output_path = Path(output_path)

    pdf_paths = sorted(
        [p for p in fixtures_dir.glob("*.pdf") if p.is_file()],
        key=lambda p: p.name,
    )
    if not pdf_paths:
        raise SystemExit(f"No PDFs found in {fixtures_dir}")

    settings = Settings()
    settings.strict_llm = bool(settings.strict_llm or strict_llm)
    settings.force_ocr = bool(settings.force_ocr or force_ocr)

    rows: list[dict[str, Any]] = []
    failures: list[str] = []

    totals = {
        "docs": 0,
        "pages": 0,
        "input_bytes": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "warnings": 0,
        "runtime_s": 0.0,
    }

    enc = tiktoken.get_encoding("cl100k_base")

    with tempfile.TemporaryDirectory(prefix="pulp_bench_") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)

        for pdf_path in pdf_paths:
            extraction = None
            start = time.perf_counter()
            try:
                detection = detect_pdf(pdf_path, settings=settings)
                extraction = extract_pdf(pdf_path, detection, settings=settings)
                cleaned = clean_extraction(extraction, settings=settings)
                structured = structure_document(cleaned, settings=settings, llm_enabled=llm_enabled)

                out_path = tmp_dir_path / f"{pdf_path.stem}.md"
                render_markdown(structured, output_path=out_path)
                output_text = out_path.read_text(encoding="utf-8")
            except LLMStructuringError as exc:
                failures.append(f"{pdf_path.name}: {exc}")
                output_text = ""
                structured = None
                detection = None
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{pdf_path.name}: {exc.__class__.__name__}: {exc}")
                output_text = ""
                structured = None
                detection = None
            end = time.perf_counter()

            raw_input_text = (
                "\n".join(p.raw_text for p in extraction.pages) if extraction is not None else ""
            )
            input_tokens = len(enc.encode(raw_input_text))
            output_tokens = len(enc.encode(output_text))

            runtime_s = end - start
            file_size = pdf_path.stat().st_size

            if detection:
                classification = str(getattr(detection.meta, "classification", ""))
                page_count = int(getattr(detection.meta, "page_count", 0))
            else:
                classification = ""
                page_count = 0
            warning_count = int(len(getattr(structured, "warnings", []) or [])) if structured else 0

            row = {
                "document": pdf_path.name,
                "classification": classification,
                "page_count": page_count,
                "input_bytes": file_size,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "warnings": warning_count,
                "runtime_s": f"{runtime_s:.3f}",
            }
            rows.append(row)

            totals["docs"] += 1
            totals["pages"] += page_count
            totals["input_bytes"] += file_size
            totals["input_tokens"] += input_tokens
            totals["output_tokens"] += output_tokens
            totals["warnings"] += warning_count
            totals["runtime_s"] += runtime_s

    md_lines: list[str] = []
    md_lines.append("# Pulp Benchmark Report")
    md_lines.append("")
    md_lines.append("Deterministic format (no timestamps). Runtime varies by machine.")
    md_lines.append("")
    md_lines.append("## Summary")
    md_lines.append("")
    md_lines.append(f"- documents: {totals['docs']}")
    md_lines.append(f"- total_pages: {totals['pages']}")
    total_input_bytes = int(totals["input_bytes"])
    md_lines.append(f"- total_input: {total_input_bytes} ({_human_bytes(total_input_bytes)})")
    md_lines.append(f"- total_input_tokens: {totals['input_tokens']}")
    md_lines.append(f"- total_output_tokens: {totals['output_tokens']}")
    md_lines.append(f"- total_warnings: {totals['warnings']}")
    md_lines.append(f"- total_runtime_s: {totals['runtime_s']:.3f}")
    md_lines.append("")
    md_lines.append("## Per-document")
    md_lines.append("")
    md_lines.append(_format_md_table(rows).rstrip())
    md_lines.append("")

    if failures:
        md_lines.append("## Failures")
        md_lines.append("")
        for failure in failures:
            md_lines.append(f"- {failure}")
        md_lines.append("")

    output_path.write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")

    if json_output_path is not None:
        payload = {
            "totals": {
                **{k: v for k, v in totals.items() if k != "runtime_s"},
                "runtime_s": round(float(totals["runtime_s"]), 6),
            },
            "rows": rows,
            "failures": failures,
            "settings": {
                "llm_enabled": bool(llm_enabled),
                "strict_llm": bool(settings.strict_llm),
                "force_ocr": bool(settings.force_ocr),
            },
        }
        json_output_path = Path(json_output_path)
        json_output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def main(argv: list[str] | None = None) -> None:
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings(
        "ignore",
        message=r"No tables found in table area.*",
        category=UserWarning,
    )

    parser = argparse.ArgumentParser(
        description="Run a deterministic Pulp benchmark over fixture PDFs."
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path("tests/fixtures/pdfs"),
        help="Directory containing PDF fixtures (default: tests/fixtures/pdfs).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark_report.md"),
        help="Markdown output path (default: benchmark_report.md).",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("benchmark.json"),
        help="JSON output path (default: benchmark.json).",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable the optional LLM structuring stage (default: off).",
    )
    parser.add_argument(
        "--strict-llm",
        action="store_true",
        help="Treat LLM failures as a hard error (exit code 4).",
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Force OCR even if the PDF appears to have a text layer.",
    )

    args = parser.parse_args(argv)

    try:
        run_benchmark(
            fixtures_dir=args.fixtures_dir,
            output_path=args.output,
            json_output_path=args.json_output,
            llm_enabled=bool(args.llm),
            strict_llm=bool(args.strict_llm),
            force_ocr=bool(args.force_ocr),
        )
    except LLMStructuringError as exc:
        raise SystemExit(4) from exc


if __name__ == "__main__":
    main()
