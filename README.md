# ssstool · 3s 工具

> 给命令行与脚本用的轻量 Python 工具包：一个 `ssstool` 入口 + 可导入的库，运行时零第三方依赖。

| 字段 | 值 |
| --- | --- |
| 包名 / 导入名 / CLI | `ssstool` / `ssstool` / `ssstool` |
| 当前版本 | `0.2.0`（Alpha，0.x 期间接口可能调整） |
| Python 支持 | `>= 3.10`（3.10 – 3.13 进入 CI） |
| 运行时依赖 | 无，仅标准库 |
| 许可证 | **PolyForm Shield 1.0.0**：可改、可分发、可商用，禁做竞品；非 OSI 开源 |
| 发布状态 | 可构建、可安装；**尚未上传 PyPI**（包名 `ssstool` 经核验未被占用） |

## 安装

```bash
# 官方 pip
pip install ssstool

# uv 项目依赖
uv add ssstool

# 一次性运行，不装进环境
uvx ssstool --version
```

从源码安装（当前可用）：

```bash
git clone https://github.com/Xlj997/ssstool.git
cd ssstool
uv sync --python 3.12
uv run ssstool --version
```

> 本机注意：PATH 上的 `python` 可能是 3.7，本项目要求 `>= 3.10`，请始终用 `uv`（`.python-version` 已锁定 3.12）。

## 30 秒上手

```console
$ ssstool --version
ssstool 0.2.0

$ ssstool doctor
status      : ok

$ ssstool browser open
pid     : 33700
cdp     : http://127.0.0.1:9222
profile : temp -> D:\proj\.ssstool\browser\<run_id>\profile

$ ssstool browser close
closed: pid 33700 (port 9222)
```

`browser open` 默认用**临时 profile**，关闭时删除；端口被占用直接报错；`--profile default`
会先终止所有 Chrome 窗口（需 `--force`，且 Chrome 136+ 拿不到 CDP）。完整参数、代理与
反检测开关见 [capabilities/browser.md](docs/capabilities/browser.md)。

## 库模式

```python
from ssstool import browser

session = browser.open_browser(port=9222)  # 默认临时 profile
try:
    print(session.pid, session.cdp_url, session.ws_url)
finally:
    browser.close_browser(port=session.port)  # 必须关闭，否则临时 profile 会留下
```

代理 + 反检测：

```python
session = browser.open_browser(
    port=9222,
    proxy="socks5://127.0.0.1:1080",  # 只支持无认证 http/https/socks5
    stealth=True,  # WebRTC/QUIC/DNS 预取/本地解析
)
```

完整 API、字段、错误码与 Playwright 接法见 [docs/library.md](docs/library.md)。

## 能力一览（导航）

| 能力 | 入口 | 状态 | 文档 |
| --- | --- | --- | --- |
| 版本查询 | `ssstool --version`、`ssstool.__version__` | 可用 | [version.md](docs/capabilities/version.md) |
| 环境自检 | `ssstool doctor` | 可用 | [doctor.md](docs/capabilities/doctor.md) |
| 打开 Chrome + CDP | `ssstool browser open` | 可用（Windows） | [browser.md](docs/capabilities/browser.md) |
| 关闭并回收 | `ssstool browser close` | 可用（Windows） | [browser.md](docs/capabilities/browser.md) |
| 代理 + 反检测参数 | `ssstool browser open --proxy ... --stealth` | 可用（Windows） | [browser.md](docs/capabilities/browser.md) |
| 查真实配置路径 | `ssstool browser profile` | 可用（Windows） | [browser.md](docs/capabilities/browser.md) |

**以 [能力登记表](docs/capabilities/README.md) 为唯一事实来源**，README 不单独承诺功能。

## 文档导航

| 文档 | 作用 |
| --- | --- |
| [docs/README.md](docs/README.md) | 文档总入口与写作规则 |
| [docs/library.md](docs/library.md) | 库模式：import 用法、API、错误码、Playwright 接法 |
| [docs/capabilities/README.md](docs/capabilities/README.md) | 能力登记表（都能干什么）+ 新增能力流程 |
| [docs/LEDGER.md](docs/LEDGER.md) | 工具发展台账：每个版本改了什么、为什么、动了哪些文件、怎么验证 |
| [docs/release-process.md](docs/release-process.md) | 发布流程 SOP：门禁、版本号、TestPyPI 演练、正式发布、回滚 |
| [docs/architecture.md](docs/architecture.md) | 工程结构、版本单一来源、CLI 约定、打包产物 |
| [AGENTS.md](AGENTS.md) | 仓库硬约束：人类与 AI 贡献者动手前必读 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 能用/不能用、分发义务与竞品边界 |

## 版本与发布

遵循 [SemVer](https://semver.org/)，`0.x` 期间不保证向后兼容：不兼容变更走 minor 并在台账标注
`BREAKING`。版本号唯一来源是 `pyproject.toml` 的 `[project].version`，发布动作只能按
[docs/release-process.md](docs/release-process.md) 执行。

## 开发

```bash
uv sync --python 3.12
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest        # Windows 下用 python -m，避开 uv trampoline 问题
uv build                       # 产物在 dist/
```

## 许可证

**PolyForm Shield License 1.0.0**：可改、可分发、可商用，但不得做成与 ssstool 竞争的产品；
非 OSI 开源。完整文本见 [LICENSE](LICENSE)，分发义务与竞争判定见
[CONTRIBUTING.md](CONTRIBUTING.md)。

## 待确认项

| 项 | 现状 | 需要谁定 |
| --- | --- | --- |
| 许可证 | 已定：PolyForm Shield 1.0.0，见 [LICENSE](LICENSE) | 已落地 |
| 作者信息 | 占位 `ssstool contributors`，建议首发前替换 | 项目所有者 |
| 0.3.0 能力方向 | 见 [能力登记表](docs/capabilities/README.md) 候选池，均未实现 | 项目所有者 |
