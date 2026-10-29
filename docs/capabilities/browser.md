# 能力：打开/关闭带 CDP 的 Chrome（browser.open / browser.close）

| 字段 | 值 |
| --- | --- |
| 能力 ID | `browser.open`、`browser.close` |
| 状态 | 可用 |
| 引入版本 | 0.2.0 |
| 平台 | Windows（x64/ARM64 均可，纯 subprocess） |
| 浏览器 | Google Chrome（注册表定位） |
| 入口 | `ssstool browser open`、`ssstool browser close`、`ssstool browser profile` |

## 能干什么

在 Windows 上启动一个**受控的 Chrome 实例**，把 CDP（Chrome DevTools Protocol）端点暴露在 `127.0.0.1:<port>`，让调用方（脚本、Agent、Playwright/Puppeteer 的 `connectOverCDP`）接管浏览器。关闭时把浏览器进程树停掉、端口释放、临时 profile 删除，做到「开得起来、关得干净」。

## 怎么用

```console
$ ssstool browser open
chrome  : C:\Users\me\AppData\Local\Google\Chrome\Application\chrome.exe
pid     : 33700
port    : 9222
cdp     : http://127.0.0.1:9222
ws      : ws://127.0.0.1:9222/devtools/browser/2930ec7c-...
version : Chrome/156.0.8078.73
profile : temp -> D:\proj\.ssstool\browser\20261029-124738-9225-54820-8af4f6\profile
```

机器可读输出（Agent 用这个）：

```console
$ ssstool browser open --json
{
  "ok": true,
  "run_id": "20261029-124738-9225-54820-8af4f6",
  "pid": 33700,
  "port": 9222,
  "profile": "temp",
  "profile_dir": "D:\\proj\\.ssstool\\browser\\20261029-124738-9225-54820-8af4f6\\profile",
  "cdp_url": "http://127.0.0.1:9222",
  "ws_url": "ws://127.0.0.1:9222/devtools/browser/2930ec7c-...",
  "browser_version": "Chrome/156.0.8078.73",
  "started_at": "2026-10-29T12:47:38+08:00"
}
```

关闭：

```console
$ ssstool browser close
closed: pid 33700 (port 9222)
profile : removed D:\proj\.ssstool\browser\20261029-124738-9225-54820-8af4f6\profile
```

真实 profile 模式（破坏性，明确失败的样子）：

```console
$ ssstool browser open --profile default --force
warning: terminated 9 Chrome process(es) before restarting with the default profile
error: Chrome was restarted with your default profile, but this Chrome build refuses remote
debugging on the default profile (Chrome 136+). The browser is left running without CDP;
use --profile temp for a reliable endpoint.                              # exit=3
```

### 参数

| 参数 | 命令 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--port` | open / close | `9222` | CDP 端口；open 时被占用直接报错，close 时用来定位会话 |
| `--profile` | open | `temp` | `temp`：独立临时 profile；`default`：**终止所有 Chrome 窗口**后用真实 profile 重启（破坏性，需 `--force`；Chrome 136+ 仍拿不到 CDP） |
| `--project-dir` | open | 当前工作目录 | 临时 profile 的归属项目根 |
| `--chrome` | open | 注册表 | 显式指定 chrome.exe |
| `--force` | open（default 必填） | 关 | 确认「终止所有 Chrome 窗口」，仅 `--profile default` 使用 |
| `--proxy` | open | 无 | 无认证代理：`http://host:port`、`https://host:port`、`socks5://host:port`；拒绝 `socks4://` 与带账号密码的 URL |
| `--proxy-bypass` | open | 无 | Chrome 的绕过列表（如 `<local>`）；必须配合 `--proxy` |
| `--stealth` | open | 关 | 反检测启动参数：禁 WebRTC 非代理 UDP、QUIC、DNS 预取，并禁止本地域名解析；必须配合 `--proxy` |
| `--timeout` | open / close | 30 / 20 秒 | 等待 CDP 就绪 / 等待进程退出 |
| `--json` | open / close | 关闭 | 输出机器可读 JSON |

### 退出码

| 码 | 含义 | 典型场景 |
| --- | --- | --- |
| 0 | 成功 | 浏览器已开且 CDP 可用；关闭已完成回收 |
| 1 | 业务失败 | 端口被占用、Chrome 未安装、端口归属不是 chrome.exe、拒绝杀未验证进程 |
| 2 | 参数/用法错误 | 端口越界、`--project-dir` 不存在、非法代理 URL、`--stealth` 缺 `--proxy` |
| 3 | CDP 不可用 | 默认 profile 模式（Chrome 136+）、Chrome 启动即退出、等待超时 |

## 代理与反检测参数（`--proxy` / `--stealth`）

```console
$ ssstool browser open --port 9222 \
    --proxy socks5://127.0.0.1:1080 \
    --proxy-bypass "<local>" \
    --stealth
proxy   : socks5://127.0.0.1:1080
bypass  : <local>
stealth : on (webrtc/quic/dns-prefetch + local DNS blocked)
```

`--stealth` 实际注入的 Chrome 启动参数：

| 参数 | 作用 |
| --- | --- |
| `--force-webrtc-ip-handling-policy=disable_non_proxied_udp` | 禁 WebRTC 走非代理 UDP，堵真实公网 IP |
| `--disable-quic` | 防 UDP 443 绕过代理 |
| `--dns-prefetch-disable` | 防预取触发本地 DNS |
| `--host-resolver-rules=MAP * ~NOTFOUND` | 本地域名解析全部失败；代理是 IP 时无需解析 |

规则与边界：

1. **只支持无认证代理**：`--proxy` 带 `user:pass@` 直接拒绝（退出码 2），提示改用本地中继注入 `Proxy-Authorization`。
2. **拒绝 `socks4://`**：SOCKS4 本地解析域名，会泄漏 DNS；用 `socks5://`（远端解析）。
3. **`--stealth` 必须配 `--proxy`**：否则 `MAP * ~NOTFOUND` 会让所有导航失败（退出码 2）。
4. **代理是域名时自动加 `EXCLUDE`**：`--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE proxy.example.com`，否则 Chrome 连代理本身都解析不了。
5. **CDP 不受影响**：调试端口绑定 `127.0.0.1` 直连，不走代理。
6. **不处理的**：DoH（建议策略 `DnsOverHttpsMode=off`）、浏览器内部服务流量、CDP 协议痕迹、IP 信誉——不在启动参数能力范围内。

实测：`--proxy http://127.0.0.1:1 --stealth` 启动后，导航返回 `net::ERR_PROXY_CONNECTION_FAILED`，证明代理与解析规则确实生效。

## 通过 import 使用（库模式）

CLI 和库共用同一套实现。`ssstool.browser` 是公开模块，函数返回 dataclass，失败统一抛 `SsstoolError`（`.code` 与 CLI 退出码一致：1 业务失败 / 2 用法错误 / 3 CDP 不可用）。

```python
from ssstool import browser
from ssstool.errors import SsstoolError

try:
    session = browser.open_browser(port=9222, profile="temp", project_dir=".")
except SsstoolError as exc:
    raise SystemExit(f"open failed ({exc.code}): {exc.message}")

try:
    print(session.pid, session.cdp_url, session.ws_url)
    # Playwright: p.chromium.connect_over_cdp(session.cdp_url)
finally:
    browser.close_browser(port=session.port)  # 必须执行，否则临时 profile 会留下
```

| 函数 | 参数（keyword-only） | 返回 |
| --- | --- | --- |
| `browser.open_browser` | `port=9222`、`profile="temp"`、`project_dir=None`、`chrome_path=None`、`timeout=30.0`、`force=False`、`proxy=None`、`proxy_bypass=None`、`stealth=False` | `Session` |
| `browser.close_browser` | `port=9222`、`timeout=20.0` | `CloseResult` |
| `browser.profile_info` | — | `dict` |

`Session` 字段：`run_id`、`pid`、`port`、`profile`、`profile_dir`、`project_dir`、`chrome`、`cdp_url`、`ws_url`、`browser_version`、`started_at`、`user_data_dir`、`user_data_dir_source`、`proxy`、`proxy_bypass`、`stealth`、`warnings`。

`CloseResult` 字段：`port`、`pid`、`already_stopped`、`profile_dir`、`profile_removed`、`warnings`。

可直接运行的完整示例：[examples/browser_import.py](../../examples/browser_import.py)；完整库模式指南（参数、错误码、Playwright 接法）见 [docs/library.md](../library.md)。

## 临时 profile 放哪：设计推理

需求是「临时目录用调用者项目的项目路径」。实际落地是 `<project>/.ssstool/browser/<run_id>/profile`，而不是直接放项目根：

| 决策 | 为什么 |
| --- | --- |
| 放调用方项目 | 调用方（脚本/Agent）以 cwd 为项目边界；profile 跟着项目走，换项目即隔离，删项目即清空，不会在全局留垃圾 |
| 多一层 `.ssstool/browser/<run_id>/` | 一个项目可能同时开多个实例（不同端口）；`run_id = 时间戳-端口-进程号-随机串` 保证不冲突 |
| 目录内自带 `.gitignore`（内容 `*`） | 不能悄悄改用户根 `.gitignore`（那是用户资产），但 profile 有几十上百 MB 且含登录态，绝不能进版本库。自忽略目录是零侵入做法 |
| cwd 不可写时回退 `%LOCALAPPDATA%\ssstool\browser\` | 只读目录、CI checkout、系统目录都可能出现；回退时 stderr 明确 warning，不静默改变行为 |
| 关闭时必须删 | 临时 profile 里有 cookie/token/缓存，留着是安全债；这也是 `temp` 与 `default` 的核心区别 |

## 真实用户配置在哪（`browser profile`）

`--profile default` 不再假设配置一定在 `...\User Data`。探测优先级：

| 优先级 | 来源 | 依据 | 说明 |
| --- | --- | --- | --- |
| 1 | `policy` | `HKLM/HKCU\SOFTWARE\Policies\Google\Chrome\UserDataDir` | 企业策略强制指定；**注册表里唯一会记录该路径的地方** |
| 2 | `running-process` | 运行中 chrome.exe 的 `--user-data-dir=` | 最权威的运行时事实；Chrome 的 crashpad 子进程会带上该参数 |
| 3 | `shortcut` | 开始菜单/桌面/任务栏 `.lnk` 的参数 | 用户把配置挪到其他盘时常见 |
| 4 | `standard` | `%LOCALAPPDATA%\Google\Chrome\User Data` | 兜底，要求存在 `Local State` 或 `Default` |

```console
$ ssstool browser profile
path     : C:\Users\me\AppData\Local\Google\Chrome\User Data
source   : running-process
standard : yes
exists   : yes

$ ssstool browser profile --json
{"ok": true, "action": "profile", "path": "...", "source": "running-process",
 "is_standard": true, "exists": true}
```

本机实测（Chrome 156）：

- 正常运行时 → `source: running-process`，路径为标准目录（浏览器进程无 flag，但 crashpad 子进程带 `--user-data-dir`）；
- 用 `--user-data-dir=D:\...\.tmp-custom-profile` 启动 → 探测到该自定义路径，`standard: no`；
- 注册表本身**没有**用户配置路径（只有 `BLBeacon` 版本、扩展、NativeMessagingHosts 等），除非设置了 `UserDataDir` 策略；
- ssstool 自己开的临时实例（路径含 `.ssstool`）会被忽略，不会污染探测结果。

## 进程与回收：为什么不是「拿到 PID 就杀」

| 坑 | 事实 | 处理 |
| --- | --- | --- |
| Popen PID 不一定可信 | Chrome 已在运行时，新进程会把请求 handoff 给已有实例并**立刻退出**；`Popen.pid` 此时是死进程 | PID 以「监听该端口的进程」为准（`GetExtendedTcpTable`），不信 Popen 返回值 |
| PID 会被复用 | 浏览器崩溃后 PID 可能被别的进程占用 | 关闭前校验 `端口归属 == 记录的 PID` 且 `镜像名 == chrome.exe`，任一不符就拒绝并报错 |
| 杀不干净 | Chrome 是多进程架构（browser/GPU/renderer/utility/crashpad） | `taskkill /PID <pid> /T /F` 杀进程树，再轮询端口直到释放 |
| 目录被占用删不掉 | Chrome 退出瞬间仍可能持有文件句柄 | 删除重试 10 次（每次 250ms），仍失败则保留路径并在 warning 里说明 |
| 树杀漏掉被重挂的 renderer | 实测 `close` 后仍残留 1 个 renderer 持有已删除的 profile 路径 | 关闭/失败回滚时按「命令行含 profile 绝对路径」兜底清理，再删目录 |
| 空目录残留 | 只删 profile 会留下 `browser/<run_id>` 空壳 | 删除后向上回收空目录，但**绝不越过 `.ssstool`** |

## 边界与限制（必读）

1. **`--profile default` 是破坏性模式**：会先 `taskkill /IM chrome.exe /T /F` 终止**所有** Chrome 窗口（含未保存表单），再重启真实 profile；未加 `--force` 直接拒绝（退出码 2）。
2. **Chrome 136+ 即使杀光所有 Chrome 也拒绝默认 profile 的远程调试**。实测本机 Chrome 156：kill 到 0 进程后，无论显式传 `--user-data-dir=<默认目录>` 还是不传，`/json/version` 都不监听。因此该模式只完成「重启浏览器」，拿不到 CDP，命令以退出码 3 结束，并**保留浏览器运行**（避免把用户搞成没有浏览器）。
3. **CDP 端口无鉴权**：能访问 `127.0.0.1:9222` 的本机进程都能控制浏览器。临时 profile 把风险限制在隔离环境；不要把 `--remote-debugging-address` 改成 `0.0.0.0`。
4. **关闭是强杀**：未提交的表单、未保存的页面会丢失。`temp` 模式符合预期；`default` 模式请谨慎。
5. 不做多标签/多页面管理，CDP 客户端自己通过 `/json/list` 操作。
6. 与手动启动的 Chrome **互不干扰**：`close` 只关闭有 ssstool 会话记录、且端口归属校验通过的实例；找不到记录时拒绝杀端口占用者。
7. 路径长度：项目路径过长 + profile 缓存可能触达 260 字符上限；长路径场景请用 `--project-dir` 指向更短的目录。
8. Windows 防火墙首次可能对监听端口弹窗；仅 `127.0.0.1`，拒绝即可（不影响本机访问）。
9. 配置探测依赖 PowerShell（`Get-CimInstance`、`WScript.Shell`）；PowerShell 不可用时退化为标准路径。
10. 仅 Windows；其他平台返回 `Windows only`（退出码 1）。
11. `--stealth` 只注入浏览器原生开关，不注入 JS、不改 CDP 痕迹、不处理 IP 信誉；高级风控仍需 IP 与行为配合。
12. `--stealth` 不强制关闭 DoH；需要时用企业策略 `DnsOverHttpsMode=off`。

## 排障

| 现象 | 判断 | 处理 |
| --- | --- | --- |
| `port 9222 is already in use` | 端口被其他程序占用 | 换 `--port`，或先关掉占用者 |
| `CDP endpoint did not become ready` | 默认 profile（Chrome 136+ 限制）/ 端口被抢 | 用 `--profile temp`；`--profile default` 只重启浏览器，不保证 CDP |
| `refusing to kill an unverified process` | 端口被非 ssstool 启动的进程占用 | 不杀；人工确认后自行处理 |
| `refusing to kill (pid reuse?)` | 记录 PID 与端口归属不一致 | 说明浏览器已崩且 PID 被复用；删除状态文件即可（路径在 `%LOCALAPPDATA%\ssstool\sessions`） |
| `profile_removed: false` | 文件仍被占用 | 等几秒手动删除；路径在 warning 里 |
| `command not found` | 未安装 | `pip install ssstool` / `uv add ssstool` |

## 实现位置

| 文件 | 作用 |
| --- | --- |
| `src/ssstool/cli.py` | `browser open/close` 子命令注册与输出格式 |
| `src/ssstool/browser.py` | 启动、代理/反检测参数注入、CDP 就绪等待、会话记录、关闭回收 |
| `src/ssstool/_win.py` | 注册表查 Chrome、**用户配置目录探测**、端口占用/归属、进程名校验、进程树终止 |
| `src/ssstool/_state.py` | 会话状态持久化（`%LOCALAPPDATA%\ssstool\sessions`） |
| `src/ssstool/errors.py` | 带退出码的业务异常 |

## 验证

`tests/test_browser.py`：

- 端口感知：`test_port_in_use_detects_listener`
- 注册表命令行解析：`test_path_from_command_quoted`、`test_path_from_command_unquoted_with_args`
- 会话状态：`test_state_roundtrip`、`test_prune_removes_dead_session`
- 临时 profile：`test_prepare_profile_creates_self_ignoring_dir`、`test_prepare_profile_rejects_missing_project_dir`
- 关闭安全：`test_close_refuses_unrecorded_listener`、`test_close_refuses_pid_reuse`、`test_close_dead_session_still_cleans_profile`、`test_kill_profile_processes_targets_only_matching`
- 配置目录探测：`test_flag_user_data_dir_parsing`、`test_running_user_data_dir_skips_ssstool_temp`、`test_resolve_user_data_dir_priority`、`test_resolve_user_data_dir_raises_when_missing`、`test_profile_info_reports_standard_flag`、`test_cli_browser_profile_prints_detected_path`
- 代理与硬化：`test_normalize_proxy_accepts_http_and_socks5`、`test_normalize_proxy_rejects_bad_input`、`test_stealth_args_disable_webrtc_quic_and_local_dns`、`test_open_stealth_requires_proxy`、`test_open_proxy_bypass_requires_proxy`、`test_open_passes_proxy_and_stealth_args`、`test_cli_browser_open_stealth_without_proxy_exits_2`
- 真实端到端（`SSSTOOL_E2E=1`）：`test_e2e_open_and_close_real_chrome` — 开、查 CDP、验 PID/端口归属、关、验目录删除与端口释放

## 变更历史

- 0.2.0：新增（见台账 v0.2.0）。
- 0.2.0（发布前补丁）：`--profile default` 改为「先终止全部 Chrome 再重启」，并要求 `--force`；实测杀光后仍无 CDP，失败时保留浏览器运行。
- 0.2.0（发布前补丁）：新增 `browser profile`，按「策略 → 运行态命令行 → 快捷方式 → 标准路径」探测真实用户配置，不再假设一定是 Default 目录。
- 0.2.0（发布前补丁）：新增 `--proxy` / `--proxy-bypass`，只支持无认证 HTTP/HTTPS/SOCKS5，拒绝 socks4 与带凭据 URL。
- 0.2.0（发布前补丁）：新增 `--stealth`，注入 WebRTC/QUIC/DNS 预取/本地解析四项原生开关，强制依赖 `--proxy`。
