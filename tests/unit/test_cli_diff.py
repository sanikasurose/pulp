from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli import app


def test_cli_diff_prints_stable_metadata_to_stderr(tmp_path: Path) -> None:
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"
    input_pdf = fixtures_dir / "pdfs" / "simple_noise.pdf"
    out_md = tmp_path / "out.md"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [str(input_pdf), "--no-llm", "--diff", "-o", str(out_md)],
    )
    assert result.exit_code == 0
    assert out_md.exists()

    err = result.stderr
    assert "classification: TEXT_LAYER" in err
    assert "page_count: 3" in err
    assert "avg_chars_per_page: 98.7" in err
    assert "warnings.extract:" in err
    assert "llm.enabled: false" in err
    assert "llm.fell_back: false" in err

    # Must not print document body to stderr.
    assert "Executive Summary" not in err
