#!/usr/bin/env python3
"""向後兼容 wrapper — 請改用: python run.py report monthly"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.reporting.cli.build_monthly import main  # noqa: E402

if __name__ == "__main__":
    main()
