from __future__ import annotations

from pathlib import Path


def run_benchmark(*, fixtures_dir: Path, output_path: Path) -> None:
    """Run the Pulp pipeline across fixture PDFs and write benchmark results to a file."""
    raise NotImplementedError
