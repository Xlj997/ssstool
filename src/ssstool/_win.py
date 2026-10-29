"""Windows 平台能力：注册表查 Chrome、端口探测/归属、进程校验与终止。

设计原则：
- 所有 Windows 专属导入都放在函数内部，模块本身可在非 Windows 上导入（便于测试）。
- 任何会「杀进程」的操作，调用方必须先通过 ``port_owner`` + ``process_name`` 双重校验，
  本模块不提供「按 PID 盲杀」的便利接口。
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

from ssstool.errors import SsstoolError

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259

_APP_PATHS = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
_START_MENU_COMMAND = r"SOFTWARE\Clients\StartMenuInternet\Google Chrome\shell\open\command"

# 注册表未命中时的最后兜底；注册表优先，路径兜底只为兼容绿色安装/旧版。
_STANDARD_SUFFIXES = (
    (r"ProgramFiles", r"Google\Chrome\Application\chrome.exe"),
    (r"ProgramFiles(x86)", r"Google\Chrome\Application\chrome.exe"),
    (r"LOCALAPPDATA", r"Google\Chrome\Application\chrome.exe"),
)


def ensure_windows() -> None:
    if sys.platform != "win32":
        raise SsstoolError(
            f"ssstool browser supports Windows only (current platform: {sys.platform}).",
            code=1,
        )


def _registry_value(root_name: str, subkey: str, name: str = "", access: int = 0) -> str | None:
    """读取注册表值；键不存在或无权限时返回 None。name 为空表示默认值。"""
    import winreg

    try:
        with winreg.OpenKey(getattr(winreg, root_name), subkey, 0, winreg.KEY_READ | access) as key:
            value, _ = winreg.QueryValueEx(key, name)
    except OSError:
        return None
    return str(value) if value else None


def _registry_default(root_name: str, subkey: str, access: int = 0) -> str | None:
    return _registry_value(root_name, subkey, "", access)


def path_from_command(command: str) -> str:
    """从注册表命令行里取出可执行文件路径（处理引号与尾随参数）。"""
    text = command.strip()
    if not text:
        return ""
    if text.startswith('"'):
        end = text.find('"', 1)
        return text[1:end] if end > 0 else text.strip('"')
    match = re.match(r"(?i)(.+?\.exe)(?:\s|$)", text)
    return match.group(1) if match else text


def find_chrome(explicit: str | os.PathLike[str] | None = None) -> Path:
    """定位 chrome.exe：显式参数 > 注册表 App Paths > 开始菜单命令 > 标准安装路径。"""
    ensure_windows()
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return candidate
        raise SsstoolError(f"--chrome path does not exist: {candidate}")

    import winreg

    targets = [
        ("HKEY_CURRENT_USER", _APP_PATHS, 0),
        ("HKEY_LOCAL_MACHINE", _APP_PATHS, winreg.KEY_WOW64_64KEY),
        ("HKEY_LOCAL_MACHINE", _APP_PATHS, winreg.KEY_WOW64_32KEY),
        ("HKEY_CURRENT_USER", _START_MENU_COMMAND, 0),
        ("HKEY_LOCAL_MACHINE", _START_MENU_COMMAND, winreg.KEY_WOW64_64KEY),
        ("HKEY_LOCAL_MACHINE", _START_MENU_COMMAND, winreg.KEY_WOW64_32KEY),
    ]
    checked: list[str] = []
    for root_name, subkey, access in targets:
        value = _registry_default(root_name, subkey, access)
        if not value:
            continue
        checked.append(f"{root_name}\\{subkey}")
        raw = path_from_command(value)
        if raw:
            candidate = Path(raw)
            if candidate.is_file():
                return candidate

    for env_name, suffix in _STANDARD_SUFFIXES:
        base = os.environ.get(env_name)
        if not base:
            continue
        candidate = Path(base) / suffix
        if candidate.is_file():
            return candidate

    raise SsstoolError(
        "Google Chrome not found. Checked registry App Paths, start-menu command and standard "
        f"install dirs ({len(checked)} registry locations). Use --chrome PATH to override.",
        code=1,
    )


def port_in_use(port: int) -> bool:
    """尝试绑定 127.0.0.1:port；绑定失败即视为被占用。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return True
    return False


def port_owner(port: int) -> int | None:
    """返回监听该端口的进程 PID（仅 IPv4 TCP LISTEN）；无监听或查询失败返回 None。"""
    ensure_windows()
    if not 0 < port < 65536:
        return None

    import ctypes
    from ctypes import wintypes

    class _Row(ctypes.Structure):
        _fields_ = [
            ("dwState", wintypes.DWORD),
            ("dwLocalAddr", wintypes.DWORD),
            ("dwLocalPort", wintypes.DWORD),
            ("dwRemoteAddr", wintypes.DWORD),
            ("dwRemotePort", wintypes.DWORD),
            ("dwOwningPid", wintypes.DWORD),
        ]

    af_inet = 2
    table_listener = 3
    error_insufficient_buffer = 122

    get_table = ctypes.WinDLL("iphlpapi.dll").GetExtendedTcpTable
    get_table.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.BOOL,
        wintypes.ULONG,
        ctypes.c_int,
        wintypes.ULONG,
    ]
    get_table.restype = wintypes.DWORD

    size = wintypes.DWORD(0)
    if (
        get_table(None, ctypes.byref(size), False, af_inet, table_listener, 0)
        != error_insufficient_buffer
    ):
        return None
    buffer = ctypes.create_string_buffer(size.value)
    if get_table(buffer, ctypes.byref(size), False, af_inet, table_listener, 0) != 0:
        return None

    count = ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD)).contents.value
    base = ctypes.addressof(buffer) + ctypes.sizeof(wintypes.DWORD)
    row_size = ctypes.sizeof(_Row)
    for index in range(count):
        row = _Row.from_address(base + index * row_size)
        local_port = socket.ntohs(row.dwLocalPort & 0xFFFF)
        if local_port == port:
            return int(row.dwOwningPid)
    return None


def pid_alive(pid: int) -> bool:
    """进程是否仍存活（不依赖 psutil）。"""
    ensure_windows()
    if pid <= 0:
        return False
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32.dll")
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def process_name(pid: int) -> str | None:
    """返回进程映像名（如 chrome.exe）；进程不存在返回 None。"""
    ensure_windows()
    if pid <= 0:
        return None
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.match(r'"([^"]+)"', result.stdout.strip())
    return match.group(1) if match else None


def kill_tree(pid: int) -> None:
    """强制结束进程及其子进程树；进程已不存在视为成功。"""
    ensure_windows()
    result = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        timeout=20,
        creationflags=CREATE_NO_WINDOW,
    )
    if result.returncode == 0 or not pid_alive(pid):
        return
    detail = (result.stderr or result.stdout or "").strip()
    raise SsstoolError(
        f"failed to terminate pid {pid}: {detail or 'taskkill returned nonzero'}", code=1
    )


def chrome_pids() -> list[int]:
    """当前所有 chrome.exe 的 PID。"""
    ensure_windows()
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    pids: list[int] = []
    for line in result.stdout.splitlines():
        match = re.match(r'"chrome\.exe","(\d+)"', line.strip(), re.IGNORECASE)
        if match:
            pids.append(int(match.group(1)))
    return pids


def kill_all_chrome(timeout: float = 15.0) -> int:
    """终止所有 chrome.exe（含子进程），返回被终止前的进程数。

    破坏性操作：调用方必须先拿到用户的显式授权（本仓库约定为 ``--force``），并打印风险提示。
    """
    ensure_windows()
    before = chrome_pids()
    if not before:
        return 0
    subprocess.run(
        ["taskkill", "/IM", "chrome.exe", "/T", "/F"],
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=CREATE_NO_WINDOW,
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not chrome_pids():
            return len(before)
        time.sleep(0.25)
    raise SsstoolError(
        "failed to terminate all chrome.exe processes; close Chrome manually and retry.", code=1
    )


_POLICIES_CHROME = r"SOFTWARE\Policies\Google\Chrome"
_DEFAULT_USER_DATA_SUFFIX = Path("Google") / "Chrome" / "User Data"


def _norm_dir(value: str | None) -> Path | None:
    """把注册表/命令行里的路径规整为存在的目录。"""
    if not value:
        return None
    raw = value.strip().strip('"')
    if not raw:
        return None
    candidate = Path(os.path.expandvars(raw))
    return candidate if candidate.is_dir() else None


def standard_chrome_user_data_dir() -> Path | None:
    """Chrome 标准用户配置目录（%LOCALAPPDATA%\\Google\\Chrome\\User Data）。"""
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        return None
    candidate = Path(base) / _DEFAULT_USER_DATA_SUFFIX
    if (candidate / "Local State").is_file() or (candidate / "Default").is_dir():
        return candidate
    return None


def _policy_user_data_dir() -> Path | None:
    """企业策略 UserDataDir —— 注册表里唯一会记录配置目录的地方。"""
    ensure_windows()
    import winreg

    for root_name, access in (
        ("HKEY_LOCAL_MACHINE", winreg.KEY_WOW64_64KEY),
        ("HKEY_CURRENT_USER", 0),
    ):
        found = _norm_dir(_registry_value(root_name, _POLICIES_CHROME, "UserDataDir", access))
        if found:
            return found
    return None


def _powershell(script: str, timeout: float = 20.0) -> str:
    """执行 PowerShell 并返回 stdout（UTF-8 解码）。"""
    preamble = "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", preamble + script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout or ""


def chrome_processes() -> list[dict[str, object]]:
    """运行中的 chrome.exe 进程（ProcessId / ParentProcessId / CommandLine）。"""
    ensure_windows()
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
        "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    )
    raw = _powershell(script).strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    if isinstance(data, dict):
        data = [data]
    return [item for item in data if isinstance(item, dict)]


def _flag_user_data_dir(command_line: str) -> Path | None:
    # Chrome 会两种写法都出现：--user-data-dir="C:\p a" 与 "--user-data-dir=C:\p a"
    match = re.search(
        r'(?:"--user-data-dir=([^"]+)"|--user-data-dir="([^"]+)"|--user-data-dir=(\S+))',
        command_line,
    )
    if not match:
        return None
    return _norm_dir(match.group(1) or match.group(2) or match.group(3))


def _is_ssstool_temp(path: Path) -> bool:
    return any(part.lower() == ".ssstool" for part in path.parts)


def _running_user_data_dir() -> Path | None:
    """运行中 Chrome 的实际 --user-data-dir；忽略 ssstool 自己开的临时实例。"""
    processes = chrome_processes()
    processes.sort(key=lambda item: "--type=" in str(item.get("CommandLine") or ""))
    for item in processes:
        found = _flag_user_data_dir(str(item.get("CommandLine") or ""))
        if found and not _is_ssstool_temp(found):
            return found
    return None


def _shortcut_user_data_dir() -> Path | None:
    """快捷方式参数里的 --user-data-dir（用户把配置挪到其他盘时常见）。"""
    script = r"""
$ws = New-Object -ComObject WScript.Shell
$paths = @(
  (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'),
  (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs'),
  (Join-Path $env:USERPROFILE 'Desktop'),
  (Join-Path $env:PUBLIC 'Desktop'),
  (Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar')
)
Get-ChildItem -Path $paths -Recurse -Filter *.lnk -ErrorAction SilentlyContinue | ForEach-Object {
  $s = $ws.CreateShortcut($_.FullName)
  if ($s.TargetPath -match 'chrome\.exe') { $s.Arguments }
}
"""
    for line in _powershell(script).splitlines():
        found = _flag_user_data_dir(line)
        if found and not _is_ssstool_temp(found):
            return found
    return None


def resolve_chrome_user_data_dir() -> tuple[Path, str]:
    """真实用户配置目录与来源。

    优先级：企业策略（注册表）> 运行中 Chrome 命令行 > 快捷方式参数 > 标准安装路径。
    注册表只在配置了 UserDataDir 策略时才记录该路径；其余情况必须从运行态或快捷方式推断，
    不能假设一定是 Default 目录。
    """
    ensure_windows()
    for resolver, source in (
        (_policy_user_data_dir, "policy"),
        (_running_user_data_dir, "running-process"),
        (_shortcut_user_data_dir, "shortcut"),
    ):
        found = resolver()
        if found:
            return found, source
    standard = standard_chrome_user_data_dir()
    if standard:
        return standard, "standard"
    raise SsstoolError(
        "could not locate the Chrome user data directory. Checked policy, running Chrome "
        "command lines, shortcuts and %LOCALAPPDATA%\\Google\\Chrome\\User Data.",
        code=1,
    )
