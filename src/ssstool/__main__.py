"""``python -m ssstool`` 入口。"""

from __future__ import annotations

import sys

from ssstool.cli import main

if __name__ == "__main__":
    sys.exit(main())
