# 架构与工程约定

> 本文回答「代码为什么这么摆、版本号从哪来、加一个命令要动哪些地方」。能力怎么用看 `docs/capabilities/`，发布怎么做看 `docs/release-process.md`。

## 1. 目标与非目标

**目标**：一个能被 `pip install` / `uv add` 装上的轻量工具包；CLI 与库两条入口共享同一份实现；版本、能力、发布三件事都有唯一事实来源。

**非目标**：不追求零成本扩展大量子命令，不引入运行时依赖，不为「框架感」做过度抽象（0.1.0 只有一层 CLI 模块 + 版本模块）。

## 2. 目录与职责

```
ssstool/
├─ pyproject.toml          元数据 / 构建 / ruff / pytest 配置；版本号唯一来源
├─ .python-version         3.12（uv 选择解释器的依据）
├─ uv.lock                 依赖锁，提交；保证 CI 与本地一致
├─ src/ssstool/
│  ├─ __init__.py          公共 API 出口（只有 __version__ / get_version）
│  ├─ _version.py          importlib.metadata 读取版本 + 源码态兜底
│  ├─ cli.py               argparse 入口、子命令注册、输出格式
│  ├─ browser.py           打开/关闭 Chrome、CDP 就绪等待、会话回收
│  ├─ _win.py              Windows：注册表查 Chrome、端口归属、进程终止
│  ├─ _state.py            会话状态持久化（LOCALAPPDATA）
│  ├─ errors.py            带退出码的 SsstoolError
│  ├─ __main__.py          python -m ssstool
│  └─ py.typed             PEP 561 标记（空文件，必须随 wheel 发布）
├─ tests/test_cli.py       冒烟回归（版本 / CLI 契约 / 打包标记）
├─ tests/test_browser.py   browser 能力单测 + 可选真实 E2E（SSSTOOL_E2E=1）
├─ docs/                   台账、发布 SOP、能力文档、本文件
└─ .github/workflows/      ci.yml（门禁）、release.yml（发布）
```

**为什么用 `src` 布局**：仓库根目录不进 `sys.path`，测试只能验证「装上的包」而不是「碰巧在当前目录下能 import 的包」。这能提前暴露打包配置错误。

**为什么 `cli.py` 不拆包**：0.1.0 只有一个命令，拆成 `commands/` 目录属于为不存在的规模支付复杂度。当子命令 ≥ 5 个时再拆，拆之前先在台账登记。

## 3. 版本号数据流（唯一来源）

```
pyproject.toml  [project].version = "0.1.0"
        │  (uv build / 安装时由构建后端写入元数据)
        ▼
ssstool-0.1.0.dist-info/METADATA  ->  Version: 0.1.0
        │  (importlib.metadata.version("ssstool"))
        ▼
ssstool._version.get_version()  ->  "0.1.0"
        │
        ▼
ssstool.__version__   /   ssstool --version
```

规则：

- **源码里不出现版本字符串**。任何 `__version__ = "0.1.0"` 的写法都是缺陷（双写必然漂移）。
- 未安装、直接跑源码时，`importlib.metadata` 抛 `PackageNotFoundError`，`get_version()` 返回 `0.0.0+source`。这是 PEP 440 合法的本地版本号，用**明显异常**的值提醒「你现在跑的不是安装态」。
- 发版只改 `pyproject.toml`（推荐 `uv version --bump`），其余全部自动跟随。

## 4. CLI 约定

### 4.1 结构

- 只用标准库 `argparse`，不引入 click/typer。
- 子命令通过 `set_defaults(handler=<函数>)` 注册；`main()` 只做 `parse → 取 handler → 调用`，新增命令不改分发逻辑。
- 每个 handler 签名为 `(args: argparse.Namespace) -> int`，返回值即退出码。

### 4.2 退出码

| 码 | 含义 | 产生方式 |
| --- | --- | --- |
| 0 | 成功 | handler 返回 0 |
| 1 | 业务失败（可预期，如校验不通过） | handler 返回 1 |
| 2 | 参数错误 | argparse 自动（`parser.error`） |

### 4.3 输出约定

- **stdout 只放结果**（人可读或可管道），**stderr 放诊断与错误**。
- **文案一律 ASCII 英文**：Windows cp936 控制台下中文会变 `���`（已实测，见台账 v0.1.0 第 6 条）。
- 帮助文本一行说清用途，不写实现细节。

### 4.4 新增子命令的 5 步

1. 在 `docs/capabilities/README.md` 登记（ID、入口、状态=开发中）。
2. 复制 `docs/capabilities/_TEMPLATE.md` 写能力文档骨架。
3. 在 `cli.py` 的 `build_parser()` 里注册解析器与 handler。
4. 补测试：happy path 至少 1 条，参数/失败路径至少 1 条。
5. 全门禁通过后，在台账记录（原因、文件、验证）。

## 5. 依赖策略

| 类别 | 策略 |
| --- | --- |
| 运行时 `dependencies` | 必须为 `[]`。引入任何依赖都要先改 `AGENTS.md` 与本文，并说明「为什么标准库做不到」 |
| 开发 `[dependency-groups].dev` | 仅 `pytest`、`ruff`；锁在 `uv.lock` |
| CI 额外工具 | 通过 `uvx <tool>` 临时拉取（如 `twine check`），不进项目依赖 |

代价先说清：零依赖意味着不能白嫖 `httpx`/`pydantic` 这类库，复杂能力可能被迫自己实现协议细节。若将来必须引入依赖，评估标准是「功能价值 > 安装体积与供应链风险」。

## 6. 打包产物

### wheel（`ssstool-0.1.0-py3-none-any.whl`）

```
ssstool/__init__.py
ssstool/__main__.py
ssstool/_version.py
ssstool/cli.py
ssstool/py.typed
ssstool-0.1.0.dist-info/{METADATA,WHEEL,entry_points.txt,RECORD}
```

- `entry_points.txt` 内容：`[console_scripts] ssstool = ssstool.cli:main`。缺它 = 装完没有命令。
- `py.typed` 为空文件但必须存在，否则类型检查器不认这个包的类型信息。
- 测试与文档**不进 wheel**（用户不需要），但进 sdist（下游发行版打包需要）。

### sdist（`ssstool-0.1.0.tar.gz`）

包含 `src/ssstool`、`tests`、`docs`、`README.md`、`AGENTS.md`、`pyproject.toml`，用于源码级安装与审计。

## 7. 测试策略

当前 7 条（`tests/test_cli.py`），全部离线、无网络、无时间依赖：

| 用例 | 锁住什么 |
| --- | --- |
| `test_version_is_pep440_ish` | 版本号格式合法 |
| `test_get_version_matches_dunder` | 版本只有一处来源，两处读法一致 |
| `test_version_flag_exits_zero` | `--version` 退出码 0 且含版本 |
| `test_no_arguments_prints_help` | 空参数不报错、能发现子命令 |
| `test_doctor_reports_environment` | `doctor` 可用且输出关键字段 |
| `test_module_entry_point_runs` | `python -m ssstool` 与 console script 等价 |
| `test_py_typed_marker_is_shipped` | 打包没漏 `py.typed` |

原则：**不 mock 自己的代码**；测 CLI 行为就用 `main(argv)` + `capsys`，测进程行为才 `subprocess`。新增子命令至少 2 条用例（成功 + 失败）。

## 8. 支持矩阵

| 项 | 范围 | 说明 |
| --- | --- | --- |
| Python | 3.10 – 3.13 | 低于 3.10 不保证；本机 PATH 的 3.7 不在支持范围 |
| 操作系统 | Windows / Linux / macOS | wheel 为 `py3-none-any`，纯 Python |
| 依赖 | 无 | 仅标准库 |

## 9. 已知环境坑

见 `AGENTS.md` 第 3 节（PATH 上的 Python 3.7、uv trampoline、控制台编码、跨分区 hardlink）。这些是实测结论，不是猜测。

## 10. browser 能力（0.2.0）

```text
cli.py (argparse)
   └─ browser.open_browser / close_browser
         ├─ _state    会话 JSON（run_id、pid、port、profile_dir、temp_profile）
         ├─ _win      注册表定位 Chrome / 用户配置目录探测 / 端口占用与归属 / 进程校验 / taskkill 树
         └─ CDP       GET http://127.0.0.1:<port>/json/version
```

四条不可动摇的规则（违反即缺陷）：

1. **PID 以端口归属为准**，不信 `Popen.pid`：Chrome 已在运行时新进程会 handoff 后退出。
2. **关闭前双校验**：端口归属 == 记录 PID，且镜像名 == `chrome.exe`；任一不符拒绝执行。
3. **临时 profile 必须删**：删除前校验路径形如 `.ssstool/browser/<run_id>/profile`，防止状态文件被篡改后删任意目录。
4. **配置目录不靠猜**：`--profile default` 的解析顺序是 策略 → 运行态 `--user-data-dir` → 快捷方式 → 标准路径；`browser profile` 把结果与来源（source）一起暴露，避免「以为在 User Data 其实不是」。
5. **代理与反检测只走原生开关**：`--proxy` / `--stealth` 通过 Chrome 命令行注入，不注入 JS、不改 CDP；`--stealth` 依赖 `--proxy`，否则 DNS 规则会破坏直连。

为什么默认 `--profile temp`：Chrome 136+ 在默认用户配置下忽略 `--remote-debugging-port`（实测本机 Chrome 156 返回空端口），而 `temp` 才能稳定拿到 CDP。`--profile default` 保留为显式选项：必须 `--force`，先终止所有 chrome.exe 再重启真实 profile；实测杀光后 Chrome 156 仍拒绝远程调试，因此失败时退出码 3、浏览器保留运行，不假装成功。
