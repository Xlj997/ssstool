# AGENTS.md — ssstool 仓库硬约束

本文件是**硬约束**，不是建议。任何人类或 AI 贡献者（含子代理）在本仓库执行写操作前必须读完本文件；与本文冲突的做法一律按缺陷处理。

一句话：**ssstool 是发布到 PyPI 的第三方包，任何改动都要经得起陌生用户在自己机器上 `pip install ssstool` 的验证。**

---

## 1. 项目边界

**是**：可 `pip install` / `uv add` 的第三方包；一个 CLI 入口 + 可导入的库；零运行时依赖的轻量工具。

**不是**：需要系统级权限的功能、需要常驻后台进程的功能、需要额外第三方依赖才能跑的功能。

- 包名、导入名、CLI 名三者必须一致：`ssstool`。不得分叉（例如包名 `ssstool` 而 CLI 叫 `sss`）。
- 需要引入任何运行时依赖 → 先改本文件第 2 节、再改 `docs/architecture.md`、最后在台账记录理由。**未记录不得合并。**

## 2. 不可违反的硬约束

1. **版本单一来源** = `pyproject.toml` 的 `[project].version`。源码里禁止出现写死的版本字符串；运行时只通过 `ssstool._version.get_version()` / `ssstool.__version__` 读取。
2. **台账纪律**：每次版本变更必须同步 `docs/LEDGER.md`，新增一条记录，写清「原因 / 变更文件 / 验证证据」。历史记录一经发布不得修改或删除，只允许插入新记录。
3. **能力登记纪律**：命令或公共函数有任何增删改，必须同步 `docs/capabilities/README.md` 登记表，并更新或新增对应能力文档。没登记的能力视为不存在。
4. **实现顺序**：先登记（登记表 + 文档骨架）→ 再实现 → 再补测试 → 最后写台账。反过来做就要返工。
5. **零运行时依赖**：`dependencies = []` 是默认状态；dev 依赖只放 `[dependency-groups].dev`。
6. **CLI 输出一律 ASCII 英文**（帮助、错误、结果）。中文只进 Markdown 文档。原因：已实测 Windows cp936 控制台/管道下中文输出乱码。
7. **不提交构建产物与本地环境**：`dist/`、`.venv/`、`.smoke*/`、`.ruff_cache/`、`.pytest_cache/` 一律不进 git。`uv.lock` **要**提交。
8. **测试必须离线可跑**：不依赖网络、系统时间、随机数、本机绝对路径。新增测试默认用 `tmp_path` / `monkeypatch`。
9. **禁止为过检查而降低标准**：不得放宽 lint/test 配置、删除断言、`skip` 用例、改测试来迁就实现。确有必要改配置，必须在台账写明原因与影响范围。
10. **发布红线**：发布只能按 `docs/release-process.md` 执行。任何 agent **不得**自行执行 `uv publish`、不得打/推 tag、不得修改已发布版本号、不得删除 PyPI 上的历史文件。
11. **浏览器回收红线**：`browser close` 只能操作通过「端口归属 == 记录 PID」且「镜像名 == chrome.exe」双重校验的进程；禁止按 PID 盲杀。临时 profile 必须删除，删除前必须校验路径形如 `.ssstool/browser/<run_id>/profile`。`--profile default` 属破坏性模式：必须要求 `--force`，执行前终止所有 chrome.exe；CDP 失败时不得杀掉刚重启的浏览器。任何放宽这些约束的实现都按安全缺陷处理。
12. **代理与反检测边界**：只支持无认证 HTTP/HTTPS/SOCKS5 代理，拒绝 `socks4://` 与带凭据的 URL；`--stealth` 只能注入浏览器原生开关，禁止注入 JS 补丁或伪装 CDP；`--stealth` 必须与 `--proxy` 同时使用。

## 3. 本机环境坑（真实踩过，必须按此执行）

| 现象 | 原因 | 正确做法 |
| --- | --- | --- |
| `python --version` 显示 3.7.9 | PATH 上是系统 Python 3.7，不是本项目的解释器 | 一律用 `uv`，`.python-version` = 3.12 |
| `uv run pytest` 报 `ERROR_OPEN_FAILED`（Windows PE resources） | uv 创建 `.exe` trampoline 时偶发失败 | 改用 `uv run python -m pytest`（不依赖 trampoline） |
| `uv build` 在同一错误上失败（装 hatchling 时生成 `hatchling.exe`） | 同上，隔离构建环境里装 hatchling 触发 trampoline | 兜底：`python -m venv <tmp>` → `<tmp>/Scripts/python -m pip install hatchling` → `<tmp>/Scripts/hatchling build`（同一 hatchling 后端，产物等价）；`uv build` 重试也常能通过 |
| Chrome 默认 profile 拿不到 CDP | Chrome 136+ 安全限制；浏览器已在运行时新进程 handoff 后退出 | 用 `--profile temp`（默认）；`--profile default` 仅显式使用，失败退出码 3 |
| 控制台中文显示为 `���` | cp936 控制台 / 管道与 UTF-8 不一致 | CLI 文案保持 ASCII（约束 6），文档不受影响 |
| `uv sync` 提示无法 hardlink | cache 与项目不在同一分区（D: / C:） | 可忽略；或设 `UV_LINK_MODE=copy` |

## 4. 目录地图

```
ssstool/
├─ pyproject.toml            构建/元数据/工具配置；版本号唯一来源
├─ .python-version           uv 解释器版本（3.12）
├─ uv.lock                   依赖锁文件，必须提交
├─ README.md                 总览 + 安装 + 导航（详细用法不放这里）
├─ AGENTS.md                 本文件：仓库硬约束
├─ LICENSE                   许可证全文（PolyForm Shield 1.0.0，非 OSI 开源）
├─ CONTRIBUTING.md           贡献规则：可做/不可做、分发义务与竞品边界
├─ src/ssstool/              源码（src 布局，禁止把包放到仓库根目录）
│  ├─ __init__.py            公共 API 出口，只导出稳定符号
│  ├─ _version.py            版本读取（importlib.metadata）
│  ├─ cli.py                 argparse 入口与子命令注册
│  ├─ browser.py            打开/关闭 Chrome、CDP 等待、会话回收
│  ├─ _win.py               注册表查 Chrome、端口归属、进程终止
│  ├─ _state.py             会话状态持久化
│  ├─ errors.py             带退出码的业务异常
│  ├─ __main__.py            python -m ssstool 入口
│  └─ py.typed               PEP 561 标记，必须随 wheel 发布
├─ tests/                    回归测试，只依赖标准库 + pytest
├─ examples/                 可运行示例（库模式），随 sdist 发布
│  └─ browser_import.py      打开/读 CDP/关闭的完整示例
├─ docs/
│  ├─ README.md              文档总入口与写作规则
│  ├─ LEDGER.md              工具发展台账（唯一版本事实来源）
│  ├─ release-process.md     发布 SOP
│  ├─ architecture.md        工程结构与约定
│  ├─ library.md             库模式（import）指南
│  └─ capabilities/          能力登记表 + 每个能力的文档
└─ .github/workflows/        CI（ci.yml）与发布（release.yml）
```

**顶层目录纪律**：`examples/` 已登记（台账 v0.2.0 第 14 条）；新增其他顶层目录（`scripts/`、`benchmarks/` 等）需先在台账登记用途再建。临时目录（`.smoke*`、`.tmp*`）用完即删。

## 5. 标准命令

```bash
# 初始化
uv sync --python 3.12

# 质量门禁（提交前必须全绿）
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest

# 构建与产物自检
uv build
uv run python -m zipfile -l dist/ssstool-*.whl

# 冒烟安装（干净环境验证「用户能装」）
uv venv .smoke --python 3.12
uv pip install --python .smoke/Scripts/python.exe dist/ssstool-*.whl   # Linux/macOS 用 .smoke/bin/python
.smoke/Scripts/ssstool.exe --version
```

## 6. Definition of Done（缺一不可）

- [ ] `uv run ruff check .` 通过
- [ ] `uv run ruff format --check .` 通过
- [ ] `uv run python -m pytest` 全绿
- [ ] `uv build` 成功，wheel 内含 `ssstool/py.typed` 与 `*.dist-info/entry_points.txt`
- [ ] 干净 venv 安装 wheel 后 `ssstool --version` 与 `ssstool doctor` 均退出码 0
- [ ] `docs/LEDGER.md` 有对应记录，且「变更文件」与实际 diff 一致
- [ ] `docs/capabilities/README.md` 与 README 能力表一致
- [ ] 版本号只存在于 `pyproject.toml`
- [ ] 没有把临时文件、构建产物、本地 venv 留在工作区

## 7. 提交与分支

- 提交信息：`type(scope): subject`，type ∈ `feat|fix|docs|chore|refactor|test|build|ci`，scope ∈ `cli|core|docs|release|deps`。
  例：`feat(cli): add doctor subcommand`、`docs(ledger): record v0.1.0`。
- 分支：`main` 受保护，日常走 `feat/<slug>`、`fix/<slug>`、`docs/<slug>`；发布不建长期分支，靠 tag。
- tag：仅发布时打 `vX.Y.Z`，指向已通过全部门禁的 `main` 提交。

## 8. 给 AI agent 的行为约束

1. 动手前按序读：`AGENTS.md`（本文件）→ `docs/LEDGER.md` 最新记录 → `docs/capabilities/README.md`。
2. **不得编造命令输出**。验证必须真的执行并贴真实结果；跑不了就写「未执行 + 原因」，不得写「已验证」。
3. 不确定的产品决策（许可证、作者信息、对外承诺、依赖引入）→ 写入「待确认项」，**不得自行拍板**，尤其许可证。
4. 改代码必须同时给测试；只改文档也要更新文档索引，避免死链。
5. 不得执行 `git push`、`git tag`、`uv publish`、`gh release`，除非人类在当轮明确授权。
6. 派发子代理时，必须在子任务 prompt 里给出本文件路径并要求其遵守。
7. 交付口径：报告「改动 + 证据 + 剩余风险」，不要把自测通过说成「已发布」。

## 9. 决策与待确认项

| 项 | 现状 | 影响 | 谁定 |
| --- | --- | --- | --- |
| 许可证 | 已定：**PolyForm Shield 1.0.0**（可改、可分发、可商用，禁止提供竞品；非 OSI 开源） | 分发必须附带许可证；判断「竞争」看 LICENSE 的 Noncompete/Competition 两节 | 项目所有者（变更需重新评估贡献政策） |
| 作者/邮箱 | 占位 `ssstool contributors` | PyPI 作者信息不准确 | 项目所有者 |
| 包描述文案 | 当前中文短句 | 影响 PyPI 搜索展示 | 项目所有者可随时调整 |
| 0.3.0 能力方向 | 候选池未排期（Edge 支持、`browser list` 等） | 决定下一版本 minor 内容 | 项目所有者 |
