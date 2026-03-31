# Pulp

[![CI](https://github.com/sanikasurose/pulp/actions/workflows/ci.yml/badge.svg)](https://github.com/sanikasurose/pulp/actions/workflows/ci.yml)
[![Benchmark](https://github.com/sanikasurose/pulp/actions/workflows/benchmark.yml/badge.svg)](https://github.com/sanikasurose/pulp/actions/workflows/benchmark.yml)

Pulp is a local-first CLI that converts PDFs (text-layer or scanned) into clean, semantically
structured Markdown suitable for LLM/RAG ingestion.

## Quickstart (local)

```bash
uv sync
uv run pulp path/to/file.pdf -o out.md
```

## OCR dependencies

Pulp uses `pdf2image` and `pytesseract`. For OCR support, you need Poppler + Tesseract installed:

- macOS: `brew install poppler tesseract`
- Ubuntu/Debian: `sudo apt-get install -y poppler-utils tesseract-ocr`

## CLI usage

```bash
uv run pulp input.pdf -o output.md
```

Common flags:

- `--force-ocr`: force OCR even if a text layer is detected
- `--diff`: print a stable per-stage metadata summary to stderr
- `--llm/--no-llm`: enable/disable the optional LLM structuring stage (default: off)
- `--strict-llm`: treat LLM failures as a hard error (exit code `4`)

## Docker

The provided `Dockerfile` includes Poppler + Tesseract and runs as a non-root user.

```bash
docker build -t pulp .
docker run --rm -v "$PWD/data:/data" pulp /data/input.pdf -o /data/output.md --diff
docker run --rm -v "$PWD/data:/data" pulp /data/input.pdf -o /data/output_ocr.md --diff --force-ocr
```

With docker-compose:

```bash
mkdir -p data
# Put a PDF at: ./data/input.pdf
docker compose run --rm pulp
docker compose run --rm pulp-ocr
```

## Benchmarking

Generate a deterministic Markdown report (format stable; runtime varies by machine):

```bash
uv run python scripts/benchmark.py
```

Example (from `tests/fixtures/pdfs/`):

| document | classification | page_count | input_bytes | output_chars | warnings | runtime_s |
| --- | --- | --- | --- | --- | --- | --- |
| simple_noise.pdf | TEXT_LAYER | 3 | 1557 | 190 | 1 | 0.613 |
| two_column.pdf | TEXT_LAYER | 1 | 1014 | 287 | 0 | 0.018 |

## Development

```bash
uv sync --group dev
uv run ruff format --check .
uv run ruff check .
uv run pytest -q --cov=src/pulp --cov-report=term-missing
```
