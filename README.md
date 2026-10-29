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

## 总览

`ssstool` 的定位是「3 秒能用」：装上就有命令可跑，不装依赖、不写配置文件、不常驻进程。当前 0.1.0 交付的是**可发布骨架**：

- 可 `pip install` / `uv add` 安装的标准第三方包结构（`src` 布局 + hatchling 构建 + wheel/sdist）；
- 唯一的 `ssstool` 命令行入口，自带 `--version` 与 `doctor` 自检，用来验证「装上了、跑得动」；
- 0.2.0 起提供第一个真实能力：Windows 下打开受控 Chrome 并暴露 CDP 端点，关闭时完整回收进程与临时 profile；
- 可 `import ssstool` 的库入口，版本号只有一处来源，不会出现「代码 0.1.0、包 0.2.0」的漂移；
- 一套交付纪律：发展台账、能力登记表、发布流程、仓库约束（`AGENTS.md`）。

能力清单见 [docs/capabilities/README.md](docs/capabilities/README.md)，**以该登记表为唯一事实来源**，README 不单独承诺功能。

## 安装

发布后（本地验证阶段请用「从源码安装」）：

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

## 快速开始

```console
$ ssstool --version
ssstool 0.1.0

$ ssstool doctor
ssstool     : 0.1.0
python      : 3.12.13 (CPython)
executable  : D:\new_job\git_code\ssstool\.venv\Scripts\python.exe
platform    : Windows-11-10.0.26200-SP0
package path: D:\new_job\git_code\ssstool\src\ssstool
status      : ok
```

作为库使用（与 CLI 同一套实现）：

```python
from ssstool import browser

session = browser.open_browser(port=9222)  # profile="temp" 是默认值
try:
    print(session.pid, session.cdp_url, session.ws_url)
finally:
    browser.close_browser(port=session.port)  # 必须关闭，否则临时 profile 会留下
```

完整可运行示例见 [examples/browser_import.py](examples/browser_import.py)，API 细节见 [browser.md](docs/capabilities/browser.md)。

## 打开带 CDP 的 Chrome（Windows）

```console
$ ssstool browser open
chrome  : C:\Users\me\AppData\Local\Google\Chrome\Application\chrome.exe
pid     : 33700
port    : 9222
cdp     : http://127.0.0.1:9222
ws      : ws://127.0.0.1:9222/devtools/browser/2930ec7c-...
version : Chrome/156.0.8078.73
profile : temp -> D:\proj\.ssstool\browser\20261029-124738-9225-54820-8af4f6\profile

$ ssstool browser close
closed: pid 33700 (port 9222)
profile : removed D:\proj\.ssstool\browser\20261029-124738-9225-54820-8af4f6\profile
```

要点（完整说明见 [browser.md](docs/capabilities/browser.md)）：

- 默认用**临时 profile**，放在调用方项目的 `.ssstool/browser/<run_id>/`，自带 `.gitignore`，关闭时删除。
- 端口默认 9222；被占用直接报错，不会静默换端口。
- `--profile default` 会**先终止所有 Chrome 窗口**（未加 `--force` 直接拒绝），再用真实 profile 重启；Chrome 136+ 即使如此也无法暴露 CDP，命令以退出码 3 结束并保留浏览器运行。默认不用。
- `close` 只杀「端口归属 = 记录 PID 且镜像是 chrome.exe」的进程，不盲杀。

## 能力一览（0.2.0）

| 能力 | 入口 | 状态 | 文档 |
| --- | --- | --- | --- |
| 版本查询 | `ssstool --version`、`ssstool.__version__` | 可用 | [version.md](docs/capabilities/version.md) |
| 环境自检 | `ssstool doctor` | 可用 | [doctor.md](docs/capabilities/doctor.md) |
| 打开 Chrome + CDP | `ssstool browser open` | 可用（Windows） | [browser.md](docs/capabilities/browser.md) |
| 关闭并回收 | `ssstool browser close` | 可用（Windows） | [browser.md](docs/capabilities/browser.md) |
| 查真实配置路径 | `ssstool browser profile` | 可用（Windows） | [browser.md](docs/capabilities/browser.md) |

## 文档引用

| 文档 | 作用 |
| --- | --- |
| [docs/README.md](docs/README.md) | 文档总入口与写作规则 |
| [docs/LEDGER.md](docs/LEDGER.md) | 工具发展台账：每个版本改了什么、为什么改、动了哪些文件、怎么验证 |
| [docs/release-process.md](docs/release-process.md) | 发布流程 SOP：门禁、版本号、TestPyPI 演练、正式发布、回滚 |
| [docs/architecture.md](docs/architecture.md) | 工程结构、版本单一来源、CLI 约定、打包产物 |
| [docs/capabilities/README.md](docs/capabilities/README.md) | 能力登记表（都能干什么）+ 新增能力流程 |
| [AGENTS.md](AGENTS.md) | 仓库硬约束：人类与 AI 贡献者动手前必读 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 能用/不能用、分发义务与竞品边界 |

## 版本与发布

遵循 [SemVer](https://semver.org/)，`0.x` 期间不保证向后兼容：不兼容变更走 minor 并在台账标注 `BREAKING`。版本号唯一来源是 `pyproject.toml` 的 `[project].version`，发布动作只能按 [docs/release-process.md](docs/release-process.md) 执行。

## 开发

```bash
uv sync --python 3.12
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest        # Windows 下用 python -m，避开 uv trampoline 问题
uv build                       # 产物在 dist/
```

## 待确认项

| 项 | 现状 | 需要谁定 |
| --- | --- | --- |
| 许可证 | 已定：CC BY-ND 4.0，见 [LICENSE](LICENSE) 与 [CONTRIBUTING.md](CONTRIBUTING.md) | 已落地 |
| 作者信息 | 占位 `ssstool contributors`，建议首发前替换 | 项目所有者 |
| 0.2.0 能力方向 | 见 [docs/capabilities/README.md](docs/capabilities/README.md) 候选池，均未实现 | 项目所有者 |

## 许可证

本项目采用 **PolyForm Shield License 1.0.0**，完整文本见 [LICENSE](LICENSE)。

一句话：**随便用、随便改、可以分发，唯独不能拿它做成跟维护者抢生意的产品。**

| 你能做什么 | 说明 |
| --- | --- |
| ✅ 使用（含商业用途） | 直接 `pip install` 或当依赖，无需申请 |
| ✅ 修改 | 可以改，改完自己用、内部用都行 |
| ✅ 分发（含修改版） | 必须随副本附带 `LICENSE` 或许可证 URL，保留 `Required Notice:` 行 |
| ❌ 做成竞品 | 不得提供与 ssstool 或维护者基于它提供的产品相竞争的产品 |
| ❌ 声称开源 | 带非竞争限制，不满足 OSI 定义 |

「竞争」的判定比直觉宽（许可证原文 Noncompete / Competition 两节）：

1. **免费也算**：哪怕你免费提供，只要它是 ssstool 的实际替代品，就构成竞争。
2. **换平台/换语言也算**：接口、平台、语言不同不影响判定；应用与服务、库与插件之间都可能构成竞争。
3. **按替代品营销 = 确定竞争**。

已知代价，先说清楚：

- 不能进 Debian/Fedora 等只收自由许可的发行版；部分企业合规扫描会报红。
- 比 MIT/Apache 采用门槛高，会挡住一部分用户——换来的是「不被 fork 抢生意」这条底线。
- 本文不构成法律建议；真要商业化维权，请让律师过一遍原文。
