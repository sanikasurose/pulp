# Pulp

Pulp is a local-first CLI tool that converts PDFs (text-layer or scanned) into clean, semantically structured Markdown suitable for LLM/RAG ingestion.

## Status

Skeleton only (no pipeline logic implemented yet).

## Install (dev)

```bash
uv sync
```

## Usage

```bash
uv run python cli.py --help
```

## Project layout

- `cli.py`: CLI entrypoint
- `src/pulp/`: pipeline package
- `tests/`: unit + integration test scaffolding

## Benchmarking

Placeholder: benchmark runner will live in `scripts/benchmark.py`.

