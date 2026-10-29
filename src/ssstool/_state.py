"""会话状态持久化。

一次 ``browser open`` = 一个 JSON 文件，放在用户级目录（LOCALAPPDATA），
这样 ``close`` 在任意 cwd 下都能找回 PID/profile。测试可用 ``SSSTOOL_STATE_DIR`` 隔离。
"""

from __future__ import annotations

import json
import os
from contextlib import suppress
from pathlib import Path
from typing import Any

STATE_DIR_ENV = "SSSTOOL_STATE_DIR"


def state_dir() -> Path:
    override = os.environ.get(STATE_DIR_ENV)
    if override:
        return Path(override).expanduser()
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "state")
    return Path(base) / "ssstool" / "sessions"


def write_session(payload: dict[str, Any]) -> Path:
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{payload['run_id']}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_sessions() -> list[tuple[Path, dict[str, Any]]]:
    directory = state_dir()
    if not directory.is_dir():
        return []
    sessions: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and "port" in data and "pid" in data:
            sessions.append((path, data))
    return sessions


def delete_session(path: Path) -> None:
    with suppress(FileNotFoundError):
        path.unlink()
