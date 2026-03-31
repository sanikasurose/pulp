from __future__ import annotations

import os
import sys
from pathlib import Path

# Keep tests deterministic regardless of developer `.env` / shell exports.
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("PULP_ANTHROPIC_MODEL", None)

# Allow tests to import the repo-root `cli.py` as `import cli`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
