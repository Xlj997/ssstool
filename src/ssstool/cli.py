"""Command line interface for ssstool.

设计约束（详见 AGENTS.md）：
- 只用标准库 ``argparse``，运行时零依赖；
- 子命令通过 ``set_defaults(handler=...)`` 注册，新增能力不改分发逻辑；
- 退出码：0 成功，1 业务失败，2 参数错误（argparse 默认 / usage），3 CDP 不可用；
- 输出一律 ASCII（含 JSON 转义），避免 Windows cp936 控制台乱码。
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from collections.abc import Sequence
from pathlib import Path

from ssstool import __version__

PROGRAM_NAME = "ssstool"
# CLI 面向管道与控制台：文案保持纯 ASCII，避免 Windows cp936 控制台 / 重定向时中文乱码。
PROGRAM_SUMMARY = "3s tool: a lightweight CLI and scripting toolkit."


def _doctor_lines() -> list[str]:
    """收集运行环境自检信息（只读，不发网络请求）。"""
    import ssstool

    package_file = getattr(ssstool, "__file__", None)
    package_path = Path(package_file).resolve().parent if package_file else "<unknown>"
    return [
        f"{PROGRAM_NAME:<12}: {__version__}",
        f"{'python':<12}: {platform.python_version()} ({platform.python_implementation()})",
        f"{'executable':<12}: {sys.executable}",
        f"{'platform':<12}: {platform.platform()}",
        f"{'package path':<12}: {package_path}",
        f"{'status':<12}: ok",
    ]


def _cmd_doctor(_args: argparse.Namespace) -> int:
    print("\n".join(_doctor_lines()))
    return 0


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid port: {value!r}") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def _cmd_browser_open(args: argparse.Namespace) -> int:
    from ssstool import browser
    from ssstool.errors import SsstoolError

    try:
        session = browser.open_browser(
            port=args.port,
            profile=args.profile,
            project_dir=args.project_dir,
            chrome_path=args.chrome,
            timeout=args.timeout,
            force=args.force,
            proxy=args.proxy,
            proxy_bypass=args.proxy_bypass,
            stealth=args.stealth,
        )
    except SsstoolError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for warning in session.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if args.json:
        print(json.dumps({"ok": True, **session.to_dict()}, ensure_ascii=True, indent=2))
        return 0

    lines = [
        f"chrome  : {session.chrome}",
        f"pid     : {session.pid}",
        f"port    : {session.port}",
        f"cdp     : {session.cdp_url}",
        f"ws      : {session.ws_url or '-'}",
        f"version : {session.browser_version or 'unknown'}",
    ]
    if session.profile_dir:
        lines.append(f"profile : {session.profile} -> {session.profile_dir}")
    elif session.user_data_dir:
        lines.append(
            f"profile : {session.profile} -> {session.user_data_dir} "
            f"(source: {session.user_data_dir_source or 'unknown'})"
        )
    else:
        lines.append(f"profile : {session.profile}")
    if session.proxy:
        lines.append(f"proxy   : {session.proxy}")
    if session.proxy_bypass:
        lines.append(f"bypass  : {session.proxy_bypass}")
    if session.stealth:
        lines.append("stealth : on (webrtc/quic/dns-prefetch + local DNS blocked)")
    print("\n".join(lines))
    return 0


def _cmd_browser_profile(args: argparse.Namespace) -> int:
    from ssstool import browser
    from ssstool.errors import SsstoolError

    try:
        info = browser.profile_info()
    except SsstoolError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"ok": True, "action": "profile", **info}, ensure_ascii=True, indent=2))
        return 0
    print(f"path     : {info['path']}")
    print(f"source   : {info['source']}")
    print(f"standard : {'yes' if info['is_standard'] else 'no'}")
    print(f"exists   : {'yes' if info['exists'] else 'no'}")
    return 0


def _cmd_browser_close(args: argparse.Namespace) -> int:
    from ssstool import browser
    from ssstool.errors import SsstoolError

    try:
        result = browser.close_browser(port=args.port, timeout=args.timeout)
    except SsstoolError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if args.json:
        print(
            json.dumps(
                {"ok": True, "action": "close", **result.to_dict()}, ensure_ascii=True, indent=2
            )
        )
        return 0

    state = "already stopped" if result.already_stopped else "closed"
    print(f"{state}: pid {result.pid} (port {result.port})")
    if result.profile_dir:
        outcome = "removed" if result.profile_removed else "kept (locked)"
        print(f"profile : {outcome} {result.profile_dir}")
    return 0


def _add_browser_commands(subparsers: argparse._SubParsersAction) -> None:
    browser = subparsers.add_parser(
        "browser", help="open or close a Chrome instance with a CDP endpoint"
    )
    actions = browser.add_subparsers(dest="browser_action", metavar="<action>", required=True)

    open_parser = actions.add_parser(
        "open", help="launch Chrome and expose a DevTools (CDP) endpoint"
    )
    open_parser.add_argument("--port", type=_port, default=9222, help="CDP port (default: 9222)")
    open_parser.add_argument(
        "--profile",
        choices=("temp", "default"),
        default="temp",
        help=(
            "temp (default): isolated profile under the caller project, deleted on close; "
            "default: restarts your real Chrome (kills ALL Chrome windows, needs --force) and "
            "normally cannot expose CDP on Chrome 136+"
        ),
    )
    open_parser.add_argument(
        "--project-dir",
        default=None,
        help="project root that owns the temp profile (default: current working directory)",
    )
    open_parser.add_argument("--chrome", default=None, help="explicit chrome.exe path")
    open_parser.add_argument("--timeout", type=float, default=30.0, help="seconds to wait for CDP")
    open_parser.add_argument(
        "--proxy",
        default=None,
        help=(
            "unauthenticated proxy URL: http://host:port, https://host:port or "
            "socks5://host:port (socks4 and credentials are rejected)"
        ),
    )
    open_parser.add_argument(
        "--proxy-bypass",
        default=None,
        help="Chrome proxy bypass list (e.g. '<local>'); requires --proxy",
    )
    open_parser.add_argument(
        "--stealth",
        action="store_true",
        help=(
            "anti-detection launch flags: disable WebRTC non-proxied UDP, QUIC and DNS "
            "prefetch, and block local DNS (requires --proxy)"
        ),
    )
    open_parser.add_argument(
        "--force",
        action="store_true",
        help="required with --profile default: terminates ALL running Chrome windows first",
    )
    open_parser.add_argument("--json", action="store_true", help="machine-readable output")
    open_parser.set_defaults(handler=_cmd_browser_open)

    close_parser = actions.add_parser(
        "close", help="stop the ssstool-launched Chrome and reclaim its profile"
    )
    close_parser.add_argument(
        "--port", type=_port, default=9222, help="CDP port of the session (default: 9222)"
    )
    close_parser.add_argument(
        "--timeout", type=float, default=20.0, help="seconds to wait for shutdown"
    )
    close_parser.add_argument("--json", action="store_true", help="machine-readable output")
    close_parser.set_defaults(handler=_cmd_browser_close)

    profile_parser = actions.add_parser(
        "profile", help="show the detected real Chrome profile directory"
    )
    profile_parser.add_argument("--json", action="store_true", help="machine-readable output")
    profile_parser.set_defaults(handler=_cmd_browser_profile)


def build_parser() -> argparse.ArgumentParser:
    """构建参数解析器；新增能力的入口统一挂在这里。"""
    parser = argparse.ArgumentParser(prog=PROGRAM_NAME, description=PROGRAM_SUMMARY)
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"{PROGRAM_NAME} {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    doctor = subparsers.add_parser("doctor", help="print runtime self-check information")
    doctor.set_defaults(handler=_cmd_doctor)

    _add_browser_commands(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI 入口；``python -m ssstool`` 与 ``ssstool`` 共用。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return int(handler(args))
