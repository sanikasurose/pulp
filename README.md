# Pulp

![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
[![CI](https://github.com/sanikasurose/pulp/actions/workflows/ci.yml/badge.svg)](https://github.com/sanikasurose/pulp/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/sanikasurose/pulp/branch/main/graph/badge.svg)](https://codecov.io/gh/sanikasurose/pulp)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=sanikasurose_pulp&metric=alert_status)](https://sonarcloud.io/project/overview?id=sanikasurose_pulp)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=sanikasurose_pulp&metric=code_smells)](https://sonarcloud.io/project/overview?id=sanikasurose_pulp)
![Tests](https://img.shields.io/badge/tests-36%20passing-brightgreen?style=flat-square)
![Coverage](https://img.shields.io/badge/coverage-86%25-brightgreen?style=flat-square)
![Models](https://img.shields.io/badge/LLM-Claude%20Haiku-orange?style=flat-square&logo=anthropic)
![Docker](https://img.shields.io/badge/docker-ready-blue?style=flat-square&logo=docker)

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
- `--diff`: print token counts and a per-stage cleaning summary to stderr
- `--verbose`: print per-stage debug logs to stderr (metadata only, no document content)
- `--llm/--no-llm`: enable/disable the optional LLM structuring stage (default: off)
- `--strict-llm`: treat LLM failures as a hard error (exit code `4`)
- `--columns [auto|off]`: multi-column layout heuristic; `auto` detects two-column PDFs automatically (default: `auto`)
- `--version`: print the installed version and exit

## LLM setup

The LLM structuring stage uses Claude Haiku via the Anthropic API. Set your key in a `.env` file
at the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Then run with `--llm`:

```bash
uv run pulp input.pdf -o output.md --diff --llm
```

If the key is missing or the API call fails, Pulp falls back to heuristic output and logs a
warning — it never crashes.

## Docker

The provided `Dockerfile` includes Poppler + Tesseract and runs as a non-root user.

```bash
docker build -t pulp .
docker run --rm -v "$PWD/data:/data" pulp /data/input.pdf -o /data/output.md --diff
docker run --rm -v "$PWD/data:/data" pulp /data/input.pdf -o /data/output_ocr.md --diff --force-ocr
```

With the LLM stage (reads key from your local `.env`):

```bash
docker run --rm -v "$HOME/Downloads:/docs" \
  -e ANTHROPIC_API_KEY="$(grep ANTHROPIC_API_KEY .env | cut -d= -f2)" \
  pulp /docs/input.pdf -o /docs/output.md --diff --llm
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

| document | classification | page_count | input_bytes | input_tokens | output_tokens | token_reduction_pct | structure_accuracy | warnings | runtime_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| simple_noise.pdf | TEXT_LAYER | 3 | 1557 | 78 | 37 | 52.6 | 100.0 | 1 | 0.620 |
| two_column.pdf | TEXT_LAYER | 1 | 1014 | 60 | 61 | -1.7 | 100.0 | 0 | 0.019 |

`structure_accuracy` is a snapshot similarity score (difflib) against manually verified expected outputs. `token_reduction_pct` is measured with tiktoken `cl100k_base`.

## Development

```bash
uv sync --group dev
uv run ruff format --check .
uv run ruff check .
uv run pytest -q --cov=src/pulp --cov-report=term-missing
```
