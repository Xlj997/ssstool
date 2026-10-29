"""ssstool — 3s 工具：轻量命令行与脚本工具包。

公共 API 只从这里导出；内部模块以下划线或 ``cli`` / 命令模块划分。
"""

from __future__ import annotations

from ssstool._version import __version__, get_version

__all__ = ["__version__", "get_version"]
