"""Access the installed distribution version from a single place.

The authoritative version lives in ``pyproject.toml`` (``[project].version``).
At runtime the value is read back from the installed distribution metadata so
that the code can never drift from the packaged version.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

DISTRIBUTION_NAME = "ssstool"
SOURCE_FALLBACK = "0.0.0+source"


def get_version() -> str:
    """Return the installed version, or a source-tree placeholder if not installed."""
    try:
        return _distribution_version(DISTRIBUTION_NAME)
    except PackageNotFoundError:
        # Running straight from the source tree without an installed distribution.
        return SOURCE_FALLBACK


__version__ = get_version()
