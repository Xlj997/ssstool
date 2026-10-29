# 库模式（import）

CLI 和库共用同一套实现。所有能力都能在 Python 里调用：函数返回 dataclass，失败抛
`SsstoolError`，`.code` 与 CLI 退出码一致。

## 安装与导入

```bash
pip install ssstool
# 或
uv add ssstool
```

```python
import ssstool
from ssstool import browser
from ssstool.errors import SsstoolError

print(ssstool.__version__)  # 0.2.0
```

## 浏览器 API

| 函数 | 参数（全部 keyword-only） | 返回 |
| --- | --- | --- |
| `browser.open_browser` | `port=9222`、`profile="temp"`、`project_dir=None`、`chrome_path=None`、`timeout=30.0`、`force=False`、`proxy=None`、`proxy_bypass=None`、`stealth=False` | `Session` |
| `browser.close_browser` | `port=9222`、`timeout=20.0` | `CloseResult` |
| `browser.profile_info` | — | `dict`（`path` / `source` / `is_standard` / `exists`） |

`open_browser` 参数速查：

| 参数 | 说明 |
| --- | --- |
| `port` | CDP 端口，默认 9222；被占用直接抛错 |
| `profile` | `"temp"`（默认，隔离 profile）或 `"default"`（真实配置，破坏性） |
| `project_dir` | 临时 profile 的归属项目根，默认当前工作目录 |
| `chrome_path` | 显式 chrome.exe 路径，默认走注册表 |
| `timeout` | 等待 CDP 就绪的秒数 |
| `force` | 仅 `profile="default"` 需要，确认终止所有 Chrome |
| `proxy` | 无认证代理：`http://host:port`、`https://host:port`、`socks5://host:port` |
| `proxy_bypass` | Chrome 绕过列表（如 `"<local>"`），需配合 `proxy` |
| `stealth` | 反检测启动开关（WebRTC/QUIC/DNS 预取/本地解析），需配合 `proxy` |

## 三种典型用法

### 1）临时 profile（默认）

```python
from ssstool import browser

session = browser.open_browser(port=9222)
try:
    print(session.pid, session.cdp_url, session.ws_url)
finally:
    browser.close_browser(port=session.port)  # 必须执行，否则临时 profile 会留下
```

### 2）代理 + 反检测

```python
session = browser.open_browser(
    port=9222,
    proxy="socks5://127.0.0.1:1080",
    proxy_bypass="<local>",
    stealth=True,
)
try:
    print(session.proxy, session.stealth)
finally:
    browser.close_browser(port=session.port)
```

规则（违反时抛 `code=2` 的 `SsstoolError`）：

- 只支持**无认证**代理；URL 里带 `user:pass@` 直接拒绝（Chrome 不支持，且会泄漏凭据）。
- 拒绝 `socks4://`（本地解析域名，泄漏 DNS），用 `socks5://`。
- `stealth=True` 必须同时给 `proxy`，否则本地 DNS 被禁、所有导航失败。

### 3）接 Playwright

```python
from playwright.sync_api import sync_playwright
from ssstool import browser

session = browser.open_browser(port=9222, proxy="socks5://127.0.0.1:1080", stealth=True)
try:
    with sync_playwright() as p:
        chrome = p.chromium.connect_over_cdp(session.cdp_url)
        page = chrome.contexts[0].pages[0]
        page.goto("https://example.com")
        print(page.title())
finally:
    browser.close_browser(port=session.port)
```

Playwright 不是本包依赖，需自行 `pip install playwright`。注意：`connect_over_cdp` **不能传
proxy**——代理必须在 `open_browser` 启动时注入，这也是本工具存在的意义之一。

## 返回值字段

`Session`：`run_id`、`pid`、`port`、`profile`、`profile_dir`、`project_dir`、`chrome`、
`cdp_url`、`ws_url`、`browser_version`、`started_at`、`user_data_dir`、
`user_data_dir_source`、`proxy`、`proxy_bypass`、`stealth`、`warnings`。

`CloseResult`：`port`、`pid`、`already_stopped`、`profile_dir`、`profile_removed`、`warnings`。

## 错误处理

```python
try:
    browser.open_browser(port=9222, proxy="socks4://127.0.0.1:1080")
except SsstoolError as exc:
    print(exc.code, exc.message)  # 2, unsupported proxy scheme ...
```

| code | 含义 | 典型场景 |
| --- | --- | --- |
| 1 | 业务失败 | 端口被占用、Chrome 未安装、拒绝杀未验证进程 |
| 2 | 参数/用法错误 | 端口越界、非法代理、`stealth` 缺 `proxy` |
| 3 | CDP 不可用 | 默认 profile（Chrome 136+）、启动即退出、等待超时 |

## 生命周期与回收

- 临时 profile 落在 `<project_dir>/.ssstool/browser/<run_id>/profile`，`close` 时删除。
- 不调用 `close` 会留下浏览器进程和 profile（含 cookie/token）。
- `close` 只杀「端口归属 == 记录 PID 且镜像名 == chrome.exe」的进程，不盲杀。
- 状态文件在 `%LOCALAPPDATA%\ssstool\sessions`，换 cwd 也能关。
- 进程崩溃/被强杀后，下次 `open` 会自动清理僵尸会话。

## 与 CLI 的对应关系

| Python | CLI |
| --- | --- |
| `browser.open_browser(port=9222, proxy=..., stealth=True)` | `ssstool browser open --port 9222 --proxy ... --stealth` |
| `browser.close_browser(port=9222)` | `ssstool browser close --port 9222` |
| `browser.profile_info()` | `ssstool browser profile --json` |

可运行示例：[examples/browser_import.py](../examples/browser_import.py)；CLI 细节与边界：
[capabilities/browser.md](capabilities/browser.md)。
