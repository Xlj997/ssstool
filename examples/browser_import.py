"""通过 import 使用 ssstool：打开受控 Chrome、读 CDP、关闭回收。

与下面两条 CLI 命令完全等价：
    ssstool browser open --port 9222
    ssstool browser close --port 9222

在仓库根目录运行：
    uv run python examples/browser_import.py

装好 wheel 之后也可以直接：
    python examples/browser_import.py
"""

from __future__ import annotations

import json
import sys
import urllib.request

from ssstool import browser
from ssstool.errors import SsstoolError

PORT = 9222


def main() -> int:
    # 1) 打开：profile="temp" 是默认值，临时目录落在 project_dir 下
    #    需要代理时：browser.open_browser(port=PORT, proxy="socks5://127.0.0.1:1080", stealth=True)
    try:
        session = browser.open_browser(port=PORT, profile="temp", project_dir=".")
    except SsstoolError as exc:
        print(f"open failed (exit={exc.code}): {exc.message}", file=sys.stderr)
        return exc.code

    print(f"opened pid={session.pid} cdp={session.cdp_url}")
    print(f"profile_dir={session.profile_dir} source={session.user_data_dir_source}")

    try:
        # 2) 用标准库直接读 CDP 的版本端点；真实项目里换成 Playwright/websocket 客户端
        with urllib.request.urlopen(f"{session.cdp_url}/json/version", timeout=5) as response:
            info = json.load(response)
        print(f"browser={info['Browser']}")
        print(f"ws={info['webSocketDebuggerUrl']}")
    finally:
        # 3) 关闭：杀进程树 + 释放端口 + 删除临时 profile
        result = browser.close_browser(port=session.port)
        print(f"closed pid={result.pid} profile_removed={result.profile_removed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
