#!/usr/bin/env python3
"""向後兼容 wrapper — 請改用: python run.py report validate <路徑>"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.reporting.cli.validate_format import main  # noqa: E402

if __name__ == "__main__":
    main()
