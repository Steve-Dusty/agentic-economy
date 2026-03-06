"""
Tests for the Trinity Scheduler Service.

This test suite validates the standalone scheduler service
without requiring the main Trinity backend.

NOTE: Path setup happens here to ensure scheduler is importable.
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
_src_path = str(_project_root / 'src')
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
