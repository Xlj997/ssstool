# ssstool 工具发展台账

> 本文件是 ssstool **版本变更的唯一事实来源**。想知道「某个能力是哪版加的、为什么加、动了哪些代码、当时怎么验证的」，只看这里。

## 使用规则

1. **一版一条记录**。每个发布（或每次版本号变更）在 `## 记录` 下方**最前面**插入一条新记录；历史记录一经发布不得改写或删除。
2. **一条记录必须回答四件事**：为什么改（触发原因）、改了哪里（文件 + 符号）、怎么验证（命令 + 真实结果）、有什么风险（兼容性 + 已知限制）。
3. **索引表同步**：新增记录后，在 `## 版本索引` 加一行，版本号就是检索键。
4. **状态口径**：`未发布` = 代码已就绪但 PyPI 上没有；`已发布` = PyPI 上有该版本且安装冒烟通过；`已撤回` = yank 或作废，必须写明原因。
5. **不写空话**。「优化了体验」「修复了若干问题」这类描述视为无效记录。

## 版本索引

| 版本 | 日期 | 类型 | 摘要 | 状态 |
| --- | --- | --- | --- | --- |
| 0.2.0 | 2026-10-29 | feat | Windows 下打开/关闭受控 Chrome 并暴露 CDP 端点（临时 profile 随项目、端口占用报错、完整回收） | 未发布 |
| 0.1.0 | 2026-10-29 | feat | 首个可发布骨架：CLI（`--version` / `doctor`）、版本单一来源、测试与文档体系 | 未发布 |

---

## 记录

### v0.2.0 — 2026-10-29 · feat

**状态**：未发布（本地单测 + 真实 Chrome E2E 通过，未上传 PyPI）

**触发原因**：第一个真实工具。需求：Windows 下用命令行打开本机 Chrome，暴露 CDP 端点（默认 9222，占用要报错），保留 PID，关闭时完整回收；默认用真实用户配置，另提供临时 profile，临时目录放在调用者项目路径。

**范围**：只做 Windows + Google Chrome + `open`/`close` 两个动作。不做多浏览器、不做标签页管理、不做 CDP 封装。

**关键实测（改变了设计，不是猜测）**

| 实验 | 结果 | 结论 |
| --- | --- | --- |
| 默认用户配置 + `--remote-debugging-port=9333` | 启动进程立即退出（handoff），端口未监听，`/json/version` 连不上 | 默认 profile 无法可靠暴露 CDP |
| 临时 `--user-data-dir` + `--remote-debugging-port=9334` | CDP 正常，`Chrome/156.0.8078.73`，端口归属 PID = 启动 PID | 临时 profile 是唯一可靠路径 |
| `taskkill /PID <pid> /T /F` 后 | 端口释放、profile 目录可删 | 回收方案可行 |

本机 Chrome `156.0.8078.73`（≥136）：默认 profile 的远程调试被安全策略关闭。因此 `--profile` 默认值定为 `temp`；`--profile default` 保留但明确不保证 CDP，失败返回退出码 3。

**变更明细**

| # | 变更 | 原因 | 文件 / 代码 | 验证 |
| --- | --- | --- | --- | --- |
| 1 | 新增 `browser open/close` 子命令 | 第一个真实能力入口 | `src/ssstool/cli.py`（`_add_browser_commands`、`_cmd_browser_open/close`） | `ssstool browser --help`；E2E 通过 |
| 2 | 注册表定位 chrome.exe | 需求要求从注册表找，且安装位置随用户变化 | `src/ssstool/_win.py::find_chrome`、`path_from_command` | 本机命中 `HKCU\...\App Paths\chrome.exe`；单测覆盖带引号/带参数解析 |
| 3 | 端口占用检测 | 需求：默认 9222，被占用必须报错 | `_win.port_in_use` | `http.server` 占 9223 后 `open` 退出码 1 并提示 |
| 4 | 端口归属 PID（GetExtendedTcpTable） | Popen PID 在 handoff 场景不可信 | `_win.port_owner` | E2E 断言 `port_owner == session.pid` |
| 5 | CDP 就绪等待 + 版本探测 | 启动是异步的，必须等 `/json/version` | `browser._wait_for_cdp`、`_read_cdp_version` | 返回 `Chrome/156.0.8078.73` 与 `webSocketDebuggerUrl` |
| 6 | 临时 profile 放调用方项目并自忽略 | 需求：临时目录用调用者项目路径；同时不能污染 git、不能留登录态 | `browser._prepare_profile`、`_ensure_self_ignoring` | `.ssstool/.gitignore` 内容为 `*`；profile 在 `<project>/.ssstool/browser/<run_id>/profile` |
| 7 | 会话状态持久化 | close 可能在别的 cwd 执行，需要跨目录找回 PID/端口/profile | `src/ssstool/_state.py` | 状态文件写入 `%LOCALAPPDATA%\ssstool\sessions\<run_id>.json` |
| 8 | 关闭双校验 + 进程树终止 + 回收 | 需求：关闭要彻底；同时不能误杀别人的 Chrome | `browser.close_browser`、`_win.kill_tree`、`_abort_launch` | 端口释放、profile 删除、状态删除；非记录进程拒绝终止 |
| 9 | 空目录回收 | 只删 profile 会留 `browser/<run_id>` 空壳 | `browser._prune_empty_parents` | close 后 `.ssstool` 下只剩 `.gitignore` |
| 10 | 默认 profile 模式明确降级 | 实测 CDP 不可得，不能假装成功 | `browser._wait_for_cdp` 的 exit 3 分支 | `--profile default` 退出码 3 + 可执行提示 |
| 11 | 版本 0.2.0 + 测试 + 文档 | 版本纪律 | `pyproject.toml`、`tests/test_browser.py`、`docs/capabilities/browser.md`、README | 24 unit passed + 1 E2E passed |
| 12 | `--profile default` 改为「先终止全部 Chrome 再重启」，强制 `--force` | 用户要求用真实配置时先杀掉所有 Chrome 再启动。实测：kill 到 0 进程后，无论是否显式传默认 `--user-data-dir`，Chrome 156 仍不监听调试端口 → 该模式只能完成「重启浏览器」，必须如实标风险 | `browser.open_browser`（force 校验 + kill_all + 失败保留浏览器）、`_win.kill_all_chrome`/`chrome_pids`、`cli.py --force` | 单测 `test_open_default_profile_requires_force`、`test_open_default_profile_kills_chrome_and_keeps_browser_on_cdp_gap`；实跑 exit=3、进程 9→9、无会话写入 |
| 13 | 真实用户配置目录探测 + `browser profile` | 用户指出真实配置可能是具体路径而非常量 Default。实测：注册表只有配置 `UserDataDir` 策略时才记录该路径；运行中的 Chrome 子进程命令行会带真实 `--user-data-dir`，快捷方式也可能带参数 → 必须按优先级探测，不能假设 | `_win.resolve_chrome_user_data_dir`（策略/运行态/快捷方式/标准路径）、`_win.chrome_processes`、`_win._flag_user_data_dir`、`browser.profile_info`、`cli.py browser profile` | 实测正常运行 → `running-process` + 标准路径；用自定义 `--user-data-dir` 启动 → 探测到自定义路径、`standard: no`；6 条新单测 |
| 14 | 新增 `examples/browser_import.py`（库模式示例）+ 库模式文档 | 用户需要 import 用法；示例必须可运行、可被 wheel 安装环境直接执行，不能是文档里的伪代码 | `examples/browser_import.py`、`pyproject.toml`（sdist include）、`docs/capabilities/browser.md`、`README.md`、`AGENTS.md` 目录地图 | 仓库内实跑 exit=0；wheel 安装后实跑 exit=0（见证据） |
| 15 | close / 失败回滚兜底清理残留 chrome 子进程 | 实测 `close` 后仍残留 1 个 renderer 持有已删除的 profile 路径（树杀漏掉被重挂的子进程），「完整回收」不成立 | `browser._kill_profile_processes`（按命令行含 profile 绝对路径匹配）、`close_browser` 与 `_abort_launch` 调用 | 修复后跑示例：`orphan_chrome=0`、端口空闲、`.ssstool/browser` 消失；单测 `test_kill_profile_processes_targets_only_matching` |
| 16 | 原生无认证代理参数 `--proxy` / `--proxy-bypass` | 用户要求只支持原生代理；中继/扩展成本高且 Chrome 137+ 不允许自动加载扩展。实现代理 URL 校验（http/https/socks5）、拒绝 socks4 与凭据、透传 Chrome `--proxy-server`/`--proxy-bypass-list` | `browser._normalize_proxy`、`open_browser` 参数、`cli.py --proxy/--proxy-bypass`、`Session.proxy/proxy_bypass` | 实跑 `--proxy http://127.0.0.1:1` → 导航 `ERR_PROXY_CONNECTION_FAILED`；非法输入 exit=2；单测 3 条 |
| 17 | 反检测启动参数 `--stealth` | 反爬调研结论：WebRTC/QUIC/DNS 属于启动期原生开关能处理的部分；CDP/JS 指纹不在本工具范围。实现 4 个原生参数，并强制依赖 `--proxy` | `browser._stealth_args`、`open_browser` 校验、`cli.py --stealth`、`Session.stealth` | 实跑命令行为包含 4 个参数；`--stealth` 缺 `--proxy` exit=2；导航被代理拦截；单测 3 条 |
| 18 | README 精简为介绍/导航 + 新增 `docs/library.md` | 工具增多后 README 里的用法会膨胀成第二个文档站；import 用法缺少集中说明；同时修正 README 里过期的 0.1.0 示例与 CC BY-ND 许可证描述 | `README.md`（重写）、`docs/library.md`（新增）、`docs/README.md`、`docs/capabilities/browser.md`、`examples/browser_import.py`、`AGENTS.md` 目录地图 | 链接检查 0 断链；`pytest` 40 passed；README 只保留安装/上手/导航，细节全部落在 `docs/` |

**验证证据**（本机 Windows，Chrome 156.0.8078.73，CPython 3.12.13）

```console
$ ssstool browser open --json
{
  "ok": true, "run_id": "20261029-124601-9222-51552-6c41f5",
  "pid": 25720, "port": 9222, "profile": "temp",
  "profile_dir": "D:\\new_job\\git_code\\ssstool\\.ssstool\\browser\\...\\profile",
  "cdp_url": "http://127.0.0.1:9222",
  "ws_url": "ws://127.0.0.1:9222/devtools/browser/f1014247-...",
  "browser_version": "Chrome/156.0.8078.73"
}                                   # exit=0

$ Invoke-RestMethod http://127.0.0.1:9222/json/version
{"Browser":"Chrome/156.0.8078.73","Protocol-Version":"1.3",
 "webSocketDebuggerUrl":"ws://127.0.0.1:9222/devtools/browser/f1014247-..."}

$ ssstool browser close --port 9222 --json
{"ok": true, "action": "close", "port": 9222, "pid": 25720,
 "already_stopped": false, "profile_removed": true, "warnings": []}
# port9222_listen=False；state 文件数=0

$ python -m http.server 9223 --bind 127.0.0.1   # 占住端口
$ ssstool browser open --port 9223
error: port 9223 is already in use. Pick another port with --port, or if it is a stale
ssstool browser run: ssstool browser close --port 9223      # exit=1，未启动新 Chrome

$ ssstool browser open --profile default --port 9224
error: --profile default terminates ALL running Chrome windows; add --force to confirm.
                                                          # exit=2，未动任何进程

$ ssstool browser open --profile default --force --port 9335
warning: terminated 9 Chrome process(es) before restarting with the default profile
error: Chrome was restarted with your default profile, but this Chrome build refuses remote
debugging on the default profile (Chrome 136+). The browser is left running without CDP;
use --profile temp for a reliable endpoint.               # exit=3，进程 9→9，无会话写入

# 补充实验（kill 到 0 进程后）：
#   显式 --user-data-dir=<默认目录> + 9333 → 端口不监听
#   不带 --user-data-dir + 9334         → 端口不监听

$ ssstool browser profile
path     : C:\Users\yafex\AppData\Local\Google\Chrome\User Data
source   : running-process
standard : yes
exists   : yes

$ # 用 --user-data-dir=D:\...\.tmp-custom-profile 启动另一个 Chrome 后再探测
path     : D:\new_job\git_code\ssstool\.tmp-custom-profile
source   : running-process
standard : no
exists   : yes

$ .venv\Scripts\python -m pytest
32 passed, 2 skipped in 1.28s

$ $env:SSSTOOL_E2E="1"; .venv\Scripts\python -m pytest tests/test_browser.py -k e2e -v
1 passed, 18 deselected in 3.82s     # 真实开/查/关一条龙

$ uv run python examples/browser_import.py
opened pid=11552 cdp=http://127.0.0.1:9222
profile_dir=D:\...\.ssstool\browser\...\profile source=temp
browser=Chrome/156.0.8078.73
ws=ws://127.0.0.1:9222/devtools/browser/3691de6f-...
closed pid=11552 profile_removed=True      # exit=0，port9222_listen=False

# 第 15 条修复前后对比：
#   修复前：close 后 orphan_chrome=1（renderer 仍持有已删除的 profile 路径）
#   修复后：orphan_chrome=0、port9222_listen=False、.ssstool/browser 已消失

$ ssstool browser open --port 9222 --proxy http://127.0.0.1:1 --stealth
proxy   : http://127.0.0.1:1
stealth : on (webrtc/quic/dns-prefetch + local DNS blocked)      # exit=0

# 实际 Chrome 命令行：
--proxy-server=http://127.0.0.1:1 --force-webrtc-ip-handling-policy=disable_non_proxied_udp
--disable-quic --dns-prefetch-disable "--host-resolver-rules=MAP * ~NOTFOUND"

# CDP 导航结果：
{"errorText": "net::ERR_PROXY_CONNECTION_FAILED"}                # 代理确实生效

$ ssstool browser open --stealth                                 # exit=2，缺 --proxy
$ ssstool browser open --proxy http://u:p@127.0.0.1:8080         # exit=2，带凭据
$ ssstool browser open --proxy socks4://127.0.0.1:1080           # exit=2，socks4 泄漏 DNS
```

**影响与兼容性**：新增命令，0.1.0 现有行为不变；`requires-python`、依赖、打包结构不变。版本按 minor 升到 0.2.0。

**已知限制**

- 仅 Windows + Chrome；Edge/Chromium 未支持。
- `--profile default` 是破坏性模式：先终止所有 Chrome（需 `--force`），且 Chrome 136+ 即便杀光所有进程仍拒绝默认配置的远程调试；失败时浏览器保留运行、退出码 3。
- `close` 是强杀（`taskkill /T /F`），未保存页面会丢。
- CDP 端口无鉴权，仅绑定 `127.0.0.1`；临时 profile 已把风险隔离。
- 未做多实例列表命令；僵尸会话在下次 `open` 时自动清理。
- 配置目录探测依赖 PowerShell（`Get-CimInstance` / `WScript.Shell`）；PowerShell 不可用时退化为标准路径。
- `--stealth` 只处理浏览器原生开关；CDP 协议痕迹、JS 指纹、IP 信誉不在范围内。
- DoH 未强制关闭，需要时用企业策略 `DnsOverHttpsMode=off`。

**下一步**

1. 支持 Edge（注册表不同键）与 `--browser` 参数。
2. 增加 `browser list` 便于排障与批量回收。
3. 按需补 CDP 轻封装（版本、目标列表），但不做全量协议实现。

---

### v0.1.0 — 2026-10-29 · feat

**状态**：未发布（本地构建 + 干净环境安装冒烟已通过，未上传 PyPI）

**触发原因**：仓库当时只有 `.git`、`.gitignore` 和一个 34 字节的 README 占位，没有任何可安装的包结构。目标是把「能 `pip install` / `uv add` 装上的第三方包」这条链路一次性拉通，并把后续迭代需要的追溯体系（台账、能力登记、发布 SOP、仓库约束）同时落地，避免以后靠口头记忆维护版本。

**范围**：包骨架 + CLI 骨架 + 交付纪律文档。**不含**业务功能（0.1.0 没有任何数据处理能力）。

**变更明细**

| # | 变更 | 原因 | 文件 / 代码 | 验证 |
| --- | --- | --- | --- | --- |
| 1 | 建立 `src` 布局与 hatchling 构建配置 | 要被 PyPI 接受，必须有 wheel + sdist；`src` 布局可防止「误把仓库根目录当包」 | `pyproject.toml`（`[build-system]`、`[tool.hatch.build.targets.*]`） | `uv build` 产出 `ssstool-0.1.0-py3-none-any.whl` 与 `.tar.gz` |
| 2 | 版本号单一来源 | 防止源码写死版本与包元数据漂移（历史高频事故） | `pyproject.toml [project].version` → `src/ssstool/_version.py::get_version()` → `ssstool.__version__` | `test_get_version_matches_dunder` 通过 |
| 3 | CLI 入口 `ssstool`（`--version`、`doctor`） | 需要一个「装完就能验证」的信号，否则无法证明包真的可用 | `src/ssstool/cli.py`、`src/ssstool/__main__.py`、`[project.scripts]` | `uv run ssstool --version` → `ssstool 0.1.0`；`doctor` 退出码 0 |
| 4 | 7 条冒烟测试 | 锁住 CLI 契约与打包标记，后续改动可回归 | `tests/test_cli.py` | `uv run python -m pytest` → 7 passed |
| 5 | ruff 配置 + `RUF001/002/003` 例外 | 中文文档的全角标点被误报为「同形字符」；这是语言选择问题不是代码缺陷 | `pyproject.toml [tool.ruff.lint] ignore` | `uv run ruff check .` → All checks passed |
| 6 | CLI 文案改为纯 ASCII 英文 | **实测**：中文帮助文本经 Windows 管道输出为 `���`，用户看到的是乱码 | `src/ssstool/cli.py`（`PROGRAM_SUMMARY`、子命令 help） | 重新执行 `ssstool` 帮助，输出无乱码 |
| 7 | 建立台账 / 能力登记 / 发布 SOP / 架构说明 / 仓库约束 | 让「为什么这么改」可追溯，让发布不靠记忆 | `docs/**`、`AGENTS.md`、`README.md` | 文档索引与文件树一一对应（见 `docs/README.md`） |
| 8 | 包名可用性核验 | 名称被占用会导致发布被拒、方案推倒重来，必须在写代码前确认 | —（外部事实） | `https://pypi.org/pypi/ssstool/json` → HTTP **404**（未被占用，核验于 2026-10-29） |
| 9 | CI 门禁 + 发布工作流 | 把「本地能跑」升级为「每次提交都验证」，并让发布走 OIDC 而不是长期 token | `.github/workflows/ci.yml`、`.github/workflows/release.yml` | YAML 解析通过（见证据）；**尚未在 GitHub 上实际运行** |
| 10 | 许可证定为 CC BY-ND 4.0 + 贡献政策 | 用户明确要求「可以使用、不能更改、建议需审核」。该组合不属于常规开源，必须有标准法律文本 + 明确的贡献边界，否则外部 PR 一合入就无法继续以该许可分发 | `LICENSE`（CC 官方全文）、`pyproject.toml [project].license`、`CONTRIBUTING.md`、`README.md` 许可证一节 | `twine check` 通过；重建 wheel 后确认 `.dist-info/licenses/LICENSE` 存在（见下文） |
| 11 | **许可证改为 PolyForm Shield 1.0.0**（取代第 10 条） | 用户澄清真实意图：「可以改、只是不能发分支抢生意」。CC BY-ND 连分享修改版都禁止，会误伤正常二次开发与内部分发，属于过度收紧；Shield 允许修改与分发，只禁止提供竞争性产品，且带专利授权条款 | `LICENSE`（PolyForm 官方 plain text）、`pyproject.toml [project].license = "LicenseRef-PolyForm-Shield-1.0.0"`、`CONTRIBUTING.md`、`README.md` 许可证一节、`AGENTS.md`、`docs/release-process.md` | `License-Expression: LicenseRef-PolyForm-Shield-1.0.0` 写入 METADATA；wheel 含 `licenses/LICENSE`；sdist 含 LICENSE + CONTRIBUTING；`twine check` PASSED（见下文） |

**验证证据**（本机：Windows，uv 0.11.2，CPython 3.12.13）

```console
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
15 files already formatted

$ uv run python -m pytest -q
.......                                                                  [100%]
7 passed

$ uv run ssstool --version
ssstool 0.1.0

$ uv run ssstool doctor
ssstool     : 0.1.0
python      : 3.12.13 (CPython)
executable  : D:\new_job\git_code\ssstool\.venv\Scripts\python.exe
platform    : Windows-11-10.0.26200-SP0
package path: D:\new_job\git_code\ssstool\src\ssstool
status      : ok
```

**干净环境安装冒烟**（用 `python -m venv` + 官方 `pip`，模拟真实用户，而非 editable 安装）：

```console
$ python -m venv .smoke
$ .smoke\Scripts\python -m pip install dist\ssstool-0.1.0-py3-none-any.whl
$ .smoke\Scripts\ssstool.exe --version
ssstool 0.1.0                       # exit=0
$ .smoke\Scripts\ssstool.exe doctor
ssstool     : 0.1.0
python      : 3.12.13 (CPython)
executable  : D:\new_job\git_code\ssstool\.smoke\Scripts\python.exe
package path: D:\new_job\git_code\ssstool\.smoke\Lib\site-packages\ssstool
status      : ok                    # exit=0
$ .smoke\Scripts\python -m pip install --force-reinstall dist\ssstool-0.1.0.tar.gz
$ .smoke\Scripts\ssstool.exe --version
ssstool 0.1.0                       # exit=0，sdist 源码安装同样可用
```

**元数据与工作流校验**：

```console
$ python -m twine check dist/*.whl dist/*.tar.gz
Checking dist\ssstool-0.1.0-py3-none-any.whl: PASSED
Checking dist\ssstool-0.1.0.tar.gz: PASSED

$ python -c "yaml.safe_load(...)"   # 逐个解析两个 workflow
ci.yml      | triggers: ['push', 'pull_request']      | jobs: ['quality', 'package-smoke']
release.yml | triggers: ['push', 'workflow_dispatch'] | jobs: ['build', 'meta', 'publish']
```

**许可证元数据与产物**（PEP 639）：

```console
$ python -c "zipfile...METADATA"
License-Expression: LicenseRef-PolyForm-Shield-1.0.0
License-File: LICENSE

wheel 内含：ssstool-0.1.0.dist-info/licenses/LICENSE
```

**构建方式说明**：首次 `uv build` 成功；随后 `uv build` 在本机连续遇到 uv 的 Windows trampoline 缺陷（安装 hatchling 时 `Failed to update Windows PE resources`，`ERROR_OPEN_FAILED`）。最终产物用同一 hatchling 后端直接构建（`python -m venv` + `python -m pip install hatchling` + `hatchling build`），产物为 `dist/ssstool-0.1.0-py3-none-any.whl`（约 13 KB，含 `licenses/LICENSE`）与 `dist/ssstool-0.1.0.tar.gz`（约 34 KB）；体积随文档更新变化。兜底命令已写入 `AGENTS.md` 第 3 节。

wheel 内容：

```
ssstool/__init__.py
ssstool/__main__.py
ssstool/_version.py
ssstool/cli.py
ssstool/py.typed
ssstool-0.1.0.dist-info/METADATA
ssstool-0.1.0.dist-info/WHEEL
ssstool-0.1.0.dist-info/entry_points.txt
ssstool-0.1.0.dist-info/RECORD
```

sdist 内容：`src/ssstool/**`、`tests/test_cli.py`、`docs/**`、`README.md`、`AGENTS.md`、`pyproject.toml`、`PKG-INFO`。

**未执行项（如实记录，不当作已验证）**

- GitHub Actions 工作流未在 GitHub 上跑过（本地只能校验 YAML 结构与触发条件）。
- PyPI / TestPyPI 未上传（无项目凭据，且 `AGENTS.md` 第 2 节第 10 条禁止 agent 自行发布）。
- Python 3.10 / 3.11 / 3.13 未在本机实测，仅由 CI 矩阵覆盖。

**影响与兼容性**

- 首个版本，无兼容性包袱。`requires-python = ">=3.10"`，运行时零依赖。
- 公共 API 仅 `ssstool.__version__`、`ssstool.get_version()`；0.x 期间其余接口不承诺稳定。
- CI 覆盖 3.10 – 3.13（见 `.github/workflows/ci.yml`），本地实测仅 3.12。

**已知限制**

- 许可证为 **PolyForm Shield 1.0.0**：非 OSI 开源、带非竞争条款、不能进 Linux 发行版；分发副本必须附带许可证文本（`README.md` 许可证一节已写明）。
- 作者信息为占位 `ssstool contributors`。
- 尚未上传 PyPI，README 中的 `pip install ssstool` 目前不可用。
- `doctor` 只做静态环境展示，不检查网络、不检查是否有新版本。
- GitHub Actions 工作流尚未在 GitHub 上实际运行，首次推送后需要观察一轮 CI 结果。
- 本机 `uv build` 存在 Windows trampoline 偶发失败，需按 `AGENTS.md` 第 3 节的兜底命令构建。

**下一步**

1. 替换作者信息占位（`[project].authors`），首发前建议做。
2. 按 `docs/release-process.md` 完成 TestPyPI 演练后首发 0.1.0。
3. 0.2.0 能力方向见 `docs/capabilities/README.md` 候选池（均为未实现提案）。

---

## 记录模板（复制后用）

```markdown
### vX.Y.Z — YYYY-MM-DD · <feat|fix|docs|chore|refactor>

**状态**：未发布 / 已发布（PyPI）/ 已撤回

**触发原因**：为什么做这件事？由什么触发（用户反馈、缺陷、依赖变化、计划）？不写「优化体验」。

**范围**：一句话说清这次改了什么、**没**改什么。

**变更明细**

| # | 变更 | 原因 | 文件 / 代码 | 验证 |
| --- | --- | --- | --- | --- |
| 1 |  |  |  |  |

**验证证据**（贴真实命令与输出，未执行的写「未执行 + 原因」）

```console
$ <command>
<output>
```

**影响与兼容性**：是否破坏兼容？升级步骤？`requires-python` 是否变化？

**已知限制**：这次没解决、但用户可能踩到的坑。

**下一步**：留给下个版本的具体动作，不写「持续优化」。
```
