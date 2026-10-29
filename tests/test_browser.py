"""browser 能力测试：端口感知、注册表解析、会话状态、关闭安全校验。

真实启动 Chrome 的用例默认跳过，设置 SSSTOOL_E2E=1 才运行。
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import pytest

from ssstool import _state, _win, browser
from ssstool.cli import main
from ssstool.errors import SsstoolError


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_port_in_use_detects_listener() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = int(sock.getsockname()[1])
        assert _win.port_in_use(port) is True
    assert _win.port_in_use(port) is False


def test_path_from_command_quoted() -> None:
    command = '"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --single-argument'
    assert _win.path_from_command(command) == (
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    )


def test_path_from_command_unquoted_with_args() -> None:
    assert _win.path_from_command("C:\\Apps\\chrome.exe --flag") == "C:\\Apps\\chrome.exe"


def test_state_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_state.STATE_DIR_ENV, str(tmp_path / "state"))
    payload = {
        "run_id": "run-1",
        "port": 9222,
        "pid": 123,
        "profile_dir": None,
        "temp_profile": True,
        "started_at": "2026-01-01T00:00:00+08:00",
    }
    path = _state.write_session(payload)
    assert path.is_file()
    sessions = _state.read_sessions()
    assert len(sessions) == 1
    assert sessions[0][1]["pid"] == 123
    _state.delete_session(path)
    assert _state.read_sessions() == []


def test_prepare_profile_creates_self_ignoring_dir(tmp_path: Path) -> None:
    profile_dir, warnings = browser._prepare_profile("temp", str(tmp_path), "run-1")
    assert profile_dir == tmp_path / ".ssstool" / "browser" / "run-1" / "profile"
    assert profile_dir is not None and profile_dir.is_dir()
    gitignore = tmp_path / ".ssstool" / ".gitignore"
    assert gitignore.is_file()
    assert "*" in gitignore.read_text(encoding="utf-8")
    assert warnings == []


def test_prepare_profile_default_has_no_dir() -> None:
    profile_dir, warnings = browser._prepare_profile("default", None, "run-1")
    assert profile_dir is None
    assert warnings == []


def test_prepare_profile_rejects_missing_project_dir(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    with pytest.raises(SsstoolError) as excinfo:
        browser._prepare_profile("temp", str(missing), "run-1")
    assert excinfo.value.code == 2


def test_owns_profile_dir_guard(tmp_path: Path) -> None:
    assert browser._owns_profile_dir(tmp_path / ".ssstool" / "browser" / "r" / "profile")
    assert not browser._owns_profile_dir(tmp_path / "profile")
    assert not browser._owns_profile_dir(tmp_path / "elsewhere" / "profile")


def test_prune_removes_dead_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_state.STATE_DIR_ENV, str(tmp_path / "state"))
    profile_dir = tmp_path / ".ssstool" / "browser" / "run-x" / "profile"
    profile_dir.mkdir(parents=True)
    _state.write_session(
        {
            "run_id": "run-x",
            "port": 9222,
            "pid": 999999,
            "profile_dir": str(profile_dir),
            "temp_profile": True,
            "started_at": "2026-01-01T00:00:00+08:00",
        }
    )
    monkeypatch.setattr(_win, "pid_alive", lambda pid: False)
    monkeypatch.setattr(_win, "port_owner", lambda port: None)

    removed = browser.prune_stale_sessions()

    assert removed == ["run-x"]
    assert not profile_dir.exists()
    assert _state.read_sessions() == []


def test_open_rejects_occupied_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    monkeypatch.setenv(
        _state.STATE_DIR_ENV, str(Path(os.environ.get("TEMP", "/tmp")) / "ssstool-test-state")
    )
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = int(sock.getsockname()[1])
        with pytest.raises(SsstoolError) as excinfo:
            browser.open_browser(port=port)
    assert "already in use" in excinfo.value.message
    assert excinfo.value.code == 1


def test_open_rejects_invalid_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    with pytest.raises(SsstoolError) as excinfo:
        browser.open_browser(port=0)
    assert excinfo.value.code == 2


def test_close_without_session_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_state.STATE_DIR_ENV, str(tmp_path / "state"))
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    monkeypatch.setattr(_win, "port_owner", lambda port: None)

    with pytest.raises(SsstoolError) as excinfo:
        browser.close_browser(port=9222)
    assert "no ssstool browser session" in excinfo.value.message


def test_close_refuses_unrecorded_listener(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_state.STATE_DIR_ENV, str(tmp_path / "state"))
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    monkeypatch.setattr(_win, "port_owner", lambda port: 4242)
    monkeypatch.setattr(_win, "process_name", lambda pid: "python.exe")

    with pytest.raises(SsstoolError) as excinfo:
        browser.close_browser(port=9222)
    assert "refusing to kill an unverified process" in excinfo.value.message


def test_close_refuses_pid_reuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_state.STATE_DIR_ENV, str(tmp_path / "state"))
    profile_dir = tmp_path / ".ssstool" / "browser" / "run-y" / "profile"
    profile_dir.mkdir(parents=True)
    _state.write_session(
        {
            "run_id": "run-y",
            "port": 9222,
            "pid": 111,
            "profile_dir": str(profile_dir),
            "temp_profile": True,
            "started_at": "2026-01-01T00:00:00+08:00",
        }
    )
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    monkeypatch.setattr(_win, "port_owner", lambda port: 222)

    with pytest.raises(SsstoolError) as excinfo:
        browser.close_browser(port=9222)
    assert "pid reuse" in excinfo.value.message
    assert profile_dir.exists()


def test_close_dead_session_still_cleans_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_state.STATE_DIR_ENV, str(tmp_path / "state"))
    profile_dir = tmp_path / ".ssstool" / "browser" / "run-z" / "profile"
    profile_dir.mkdir(parents=True)
    _state.write_session(
        {
            "run_id": "run-z",
            "port": 9222,
            "pid": 111,
            "profile_dir": str(profile_dir),
            "temp_profile": True,
            "started_at": "2026-01-01T00:00:00+08:00",
        }
    )
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    monkeypatch.setattr(_win, "port_owner", lambda port: None)
    monkeypatch.setattr(_win, "pid_alive", lambda pid: False)
    monkeypatch.setattr(_win, "chrome_processes", lambda: [])

    result = browser.close_browser(port=9222)

    assert result.already_stopped is True
    assert result.profile_removed is True
    assert not profile_dir.exists()
    assert _state.read_sessions() == []


def test_kill_profile_processes_targets_only_matching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = tmp_path / ".ssstool" / "browser" / "run-p" / "profile"
    profile.mkdir(parents=True)
    other = (tmp_path / "other-profile").as_posix()
    monkeypatch.setattr(
        _win,
        "chrome_processes",
        lambda: [
            {"ProcessId": 11, "CommandLine": f'"chrome.exe" --user-data-dir={profile}'},
            {"ProcessId": 22, "CommandLine": f'"chrome.exe" --user-data-dir={other}'},
        ],
    )
    killed: list[int] = []
    monkeypatch.setattr(_win, "kill_tree", lambda pid: killed.append(pid))

    result = browser._kill_profile_processes(profile)

    assert result == [11]
    assert killed == [11]


def test_cli_rejects_out_of_range_port() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["browser", "open", "--port", "70000"])
    assert excinfo.value.code == 2


def test_cli_browser_requires_action() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["browser"])
    assert excinfo.value.code == 2


@pytest.mark.skipif(sys.platform == "win32", reason="platform guard only fires off Windows")
def test_cli_open_platform_guard(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["browser", "open"]) == 1
    assert "Windows only" in capsys.readouterr().err


def test_open_default_profile_requires_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_state.STATE_DIR_ENV, str(tmp_path / "state"))
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)

    with pytest.raises(SsstoolError) as excinfo:
        browser.open_browser(profile="default")
    assert excinfo.value.code == 2
    assert "--force" in excinfo.value.message


def test_open_default_profile_kills_chrome_and_keeps_browser_on_cdp_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_state.STATE_DIR_ENV, str(tmp_path / "state"))
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    monkeypatch.setattr(_win, "port_in_use", lambda port: False)
    monkeypatch.setattr(_win, "find_chrome", lambda explicit=None: Path("chrome.exe"))
    user_dir = tmp_path / "User Data"
    user_dir.mkdir()
    monkeypatch.setattr(_win, "resolve_chrome_user_data_dir", lambda: (user_dir, "running-process"))
    monkeypatch.setattr(_win, "standard_chrome_user_data_dir", lambda: user_dir)
    calls: list[str] = []
    launched: list[Path | None] = []
    monkeypatch.setattr(_win, "kill_all_chrome", lambda: calls.append("kill") or 3)
    monkeypatch.setattr(
        browser,
        "_launch",
        lambda chrome, port, data_dir, extra_args=None: launched.append(data_dir) or object(),
    )

    def fake_wait(*args: object, **kwargs: object) -> dict[str, object]:
        raise SsstoolError("no cdp", code=3)

    monkeypatch.setattr(browser, "_wait_for_cdp", fake_wait)

    with pytest.raises(SsstoolError) as excinfo:
        browser.open_browser(port=9222, profile="default", force=True)

    assert excinfo.value.code == 3
    assert "left running" in excinfo.value.message
    assert str(user_dir) in excinfo.value.message
    assert calls == ["kill"]
    assert launched == [user_dir]
    assert _state.read_sessions() == []


def test_flag_user_data_dir_parsing(tmp_path: Path) -> None:
    real = tmp_path / "Real Profile"
    real.mkdir()
    plain = tmp_path / "RealProfile"
    plain.mkdir()
    assert _win._flag_user_data_dir(f'--user-data-dir="{real}"') == real
    assert _win._flag_user_data_dir(f'"--user-data-dir={real}"') == real
    assert _win._flag_user_data_dir(f"--user-data-dir={plain}") == plain
    assert _win._flag_user_data_dir("--type=renderer") is None


def test_running_user_data_dir_skips_ssstool_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "RealProfile"
    real.mkdir()
    temp = tmp_path / ".ssstool" / "browser" / "run" / "profile"
    temp.mkdir(parents=True)
    monkeypatch.setattr(
        _win,
        "chrome_processes",
        lambda: [
            {"CommandLine": f'"chrome.exe" --user-data-dir={temp}'},
            {"CommandLine": f'"chrome.exe" --user-data-dir={real}'},
        ],
    )
    assert _win._running_user_data_dir() == real


def test_resolve_user_data_dir_priority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy = tmp_path / "policy"
    policy.mkdir()
    running = tmp_path / "running"
    running.mkdir()
    standard = tmp_path / "standard"
    standard.mkdir()
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    monkeypatch.setattr(_win, "_shortcut_user_data_dir", lambda: None)
    monkeypatch.setattr(_win, "standard_chrome_user_data_dir", lambda: standard)
    monkeypatch.setattr(_win, "_policy_user_data_dir", lambda: policy)
    monkeypatch.setattr(_win, "_running_user_data_dir", lambda: running)

    assert _win.resolve_chrome_user_data_dir() == (policy, "policy")
    monkeypatch.setattr(_win, "_policy_user_data_dir", lambda: None)
    assert _win.resolve_chrome_user_data_dir() == (running, "running-process")
    monkeypatch.setattr(_win, "_running_user_data_dir", lambda: None)
    assert _win.resolve_chrome_user_data_dir() == (standard, "standard")


def test_resolve_user_data_dir_raises_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    monkeypatch.setattr(_win, "_policy_user_data_dir", lambda: None)
    monkeypatch.setattr(_win, "_running_user_data_dir", lambda: None)
    monkeypatch.setattr(_win, "_shortcut_user_data_dir", lambda: None)
    monkeypatch.setattr(_win, "standard_chrome_user_data_dir", lambda: None)

    with pytest.raises(SsstoolError) as excinfo:
        _win.resolve_chrome_user_data_dir()
    assert excinfo.value.code == 1
    assert "could not locate" in excinfo.value.message


def test_profile_info_reports_standard_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = tmp_path / "User Data"
    profile.mkdir()
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    monkeypatch.setattr(_win, "resolve_chrome_user_data_dir", lambda: (profile, "standard"))
    monkeypatch.setattr(_win, "standard_chrome_user_data_dir", lambda: profile)

    info = browser.profile_info()

    assert info == {
        "path": str(profile),
        "source": "standard",
        "is_standard": True,
        "exists": True,
    }


def test_cli_browser_profile_prints_detected_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        browser,
        "profile_info",
        lambda: {
            "path": "C:/Users/me/AppData/Local/Google/Chrome/User Data",
            "source": "running-process",
            "is_standard": False,
            "exists": True,
        },
    )
    assert main(["browser", "profile"]) == 0
    out = capsys.readouterr().out
    assert "running-process" in out
    assert "User Data" in out


def test_normalize_proxy_accepts_http_and_socks5() -> None:
    assert browser._normalize_proxy("socks5://127.0.0.1:1080") == "socks5://127.0.0.1:1080"
    assert browser._normalize_proxy("HTTP://proxy.local:3128") == "http://proxy.local:3128"
    assert browser._normalize_proxy("socks5://127.0.0.1:1080/") == "socks5://127.0.0.1:1080"
    assert browser._normalize_proxy("socks5://[::1]:1080") == "socks5://[::1]:1080"


def test_normalize_proxy_rejects_bad_input() -> None:
    for value in (
        "socks4://127.0.0.1:1080",
        "http://user:pass@127.0.0.1:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:8080/path",
        "http://127.0.0.1:notaport",
    ):
        with pytest.raises(SsstoolError) as excinfo:
            browser._normalize_proxy(value)
        assert excinfo.value.code == 2


def test_stealth_args_disable_webrtc_quic_and_local_dns() -> None:
    args = browser._stealth_args("socks5://127.0.0.1:1080")
    assert "--force-webrtc-ip-handling-policy=disable_non_proxied_udp" in args
    assert "--disable-quic" in args
    assert "--dns-prefetch-disable" in args
    rule = next(item for item in args if item.startswith("--host-resolver-rules="))
    assert "MAP * ~NOTFOUND" in rule
    assert "EXCLUDE" not in rule

    host_rule = next(
        item
        for item in browser._stealth_args("http://proxy.example.com:3128")
        if item.startswith("--host-resolver-rules=")
    )
    assert "EXCLUDE proxy.example.com" in host_rule


def test_open_stealth_requires_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    with pytest.raises(SsstoolError) as excinfo:
        browser.open_browser(port=9222, stealth=True)
    assert excinfo.value.code == 2
    assert "--stealth requires --proxy" in excinfo.value.message


def test_open_proxy_bypass_requires_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    with pytest.raises(SsstoolError) as excinfo:
        browser.open_browser(port=9222, proxy_bypass="<local>")
    assert excinfo.value.code == 2


def test_open_passes_proxy_and_stealth_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_state.STATE_DIR_ENV, str(tmp_path / "state"))
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    monkeypatch.setattr(_win, "port_in_use", lambda port: False)
    monkeypatch.setattr(_win, "find_chrome", lambda explicit=None: Path("chrome.exe"))
    monkeypatch.setattr(browser, "prune_stale_sessions", lambda: [])
    profile_dir = tmp_path / ".ssstool" / "browser" / "run-p" / "profile"
    profile_dir.mkdir(parents=True)
    monkeypatch.setattr(browser, "_prepare_profile", lambda *args: (profile_dir, []))
    captured: list[list[str]] = []
    monkeypatch.setattr(
        browser,
        "_launch",
        lambda chrome, port, data_dir, extra_args=None: (
            captured.append(list(extra_args or [])) or object()
        ),
    )
    monkeypatch.setattr(
        browser,
        "_wait_for_cdp",
        lambda *args, **kwargs: {
            "Browser": "Chrome/156",
            "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/x",
        },
    )
    monkeypatch.setattr(_win, "port_owner", lambda port: 4321)
    monkeypatch.setattr(_win, "process_name", lambda pid: "chrome.exe")

    session = browser.open_browser(
        port=9222,
        proxy="socks5://127.0.0.1:1080",
        proxy_bypass="<local>",
        stealth=True,
    )

    assert captured == [
        [
            "--proxy-server=socks5://127.0.0.1:1080",
            "--proxy-bypass-list=<local>",
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
            "--disable-quic",
            "--dns-prefetch-disable",
            "--host-resolver-rules=MAP * ~NOTFOUND",
        ]
    ]
    assert session.proxy == "socks5://127.0.0.1:1080"
    assert session.proxy_bypass == "<local>"
    assert session.stealth is True


def test_cli_browser_open_stealth_without_proxy_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(_win, "ensure_windows", lambda: None)
    assert main(["browser", "open", "--stealth"]) == 2
    assert "--stealth requires --proxy" in capsys.readouterr().err


@pytest.mark.e2e
@pytest.mark.skipif(os.environ.get("SSSTOOL_E2E") != "1", reason="set SSSTOOL_E2E=1 to run")
def test_e2e_open_and_close_real_chrome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_state.STATE_DIR_ENV, str(tmp_path / "state"))
    port = _free_port()
    session = browser.open_browser(
        port=port, profile="temp", project_dir=str(tmp_path), timeout=45.0
    )
    try:
        assert session.cdp_url == f"http://127.0.0.1:{port}"
        assert session.browser_version
        assert session.profile_dir and Path(session.profile_dir).is_dir()
        assert (tmp_path / ".ssstool" / ".gitignore").is_file()
        assert _win.port_owner(port) == session.pid
    finally:
        result = browser.close_browser(port=port, timeout=30.0)

    assert result.profile_removed is True
    assert session.profile_dir and not Path(session.profile_dir).exists()
    assert _win.port_owner(port) is None
