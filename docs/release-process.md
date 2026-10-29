# ssstool 发布流程（PyPI）

> 目标：任何人按本文操作，都能把某个 `main` 提交变成一个**用户 `pip install ssstool` 真能装上、真能跑**的版本；出错时知道怎么止损。

**核心事实**：PyPI 上的版本号**一次性的、不可回收**。同名同版本一旦上传就不能覆盖；删除文件后该版本号永久不可再用。所以流程的重点不是「传得快」，而是「传之前确认清楚」。

---

## 0. 发布模型

- 包名 `ssstool`，发布源 = GitHub 仓库 `Xlj997/ssstool` 的 `main` 分支上某个通过全部门禁的提交。
- 版本号唯一来源：`pyproject.toml` 的 `[project].version`。
- 触发方式：**推 tag `vX.Y.Z` → GitHub Actions（`.github/workflows/release.yml`）用 Trusted Publishing 上传**。人工只负责打 tag，不碰 token。
- 预发布 / 演练：`workflow_dispatch` 选择 `testpypi`，或推 `vX.Y.ZrcN` 这类 tag（工作流会路由到 TestPyPI）。
- 禁止：本地 `uv publish` 直传正式 PyPI（仅作为 CI 故障时的兜底，且必须人类当场授权）。

---

## 1. 一次性准备（G0，只做一次）

| # | 事项 | 操作 | 验收 |
| --- | --- | --- | --- |
| 1 | PyPI 账号 | 注册并**开启 2FA**（未开 2FA 无法发布） | 登录成功 |
| 2 | 名称可用性 | `Invoke-RestMethod https://pypi.org/pypi/ssstool/json` 应返回 404 | 404 = 未被占用（2026-10-29 已核验） |
| 3 | Trusted Publisher | PyPI → Account settings → **Publishing** → 添加 *pending publisher*：Project `ssstool`、Owner `Xlj997`、Repository `ssstool`、Workflow `release.yml`、Environment `pypi` | 列表中出现该条目 |
| 4 | GitHub Environment | 仓库 Settings → Environments 新建 `pypi`（建议加 required reviewers）、`testpypi` | 两个 environment 存在 |
| 5 | TestPyPI（可选但强烈建议） | test.pypi.org 注册 + 同样配 pending publisher（Environment `testpypi`） | 能用 testpypi 演练 |
| 6 | 许可证与作者信息 | 许可证已定：PolyForm Shield 1.0.0（见 [LICENSE](../LICENSE)）；作者信息仍为占位，首发前建议替换 | `pyproject.toml` 有 `license = "LicenseRef-PolyForm-Shield-1.0.0"`，`LICENSE` 文件存在 |

> G0 未完成时，tag 推上去 CI 会以 `403` / `trusted publishing` 错误失败——这是配置问题，不是代码问题。

---

## 2. 版本号决策

遵循 SemVer；`0.x` 期间不承诺向后兼容。

| 变更类型 | 0.x 期间 | 1.0+ | 示例 |
| --- | --- | --- | --- |
| 修 bug、无接口变化 | patch | patch | `0.1.0 → 0.1.1` |
| 新增能力、向后兼容 | minor | minor | `0.1.1 → 0.2.0` |
| 破坏性变更 | minor + 台账标 `BREAKING` | major | `0.2.0 → 0.3.0` |
| 预发布演练 | `X.Y.ZaN` / `bN` / `rcN` | 同左 | `0.2.0rc1` |
| 纯文档修正（需刷新 PyPI 页面） | patch | patch | `0.1.1 → 0.1.2` |

```powershell
uv version --bump patch   # 或 minor / major / rc
uv version --short        # 确认结果，例如 0.1.1
```

`uv version` 会同步改写 `pyproject.toml` 与 `uv.lock`，**不要**手工在两处分别改。

---

## 3. 发布门禁（G1 – G7）

按顺序跑，任何一项不通过就停，**不允许「先发出去再修」**。

| 门禁 | 检查内容 | 命令 | 通过标准 |
| --- | --- | --- | --- |
| **G1** 版本与记录 | 版本号与台账、能力登记一致；许可证已定 | 人工核对 `pyproject.toml`、`docs/LEDGER.md`、`docs/capabilities/README.md` | 台账有本版本记录；能力表与 README 一致；`license` 已填 |
| **G2** 代码质量 | lint、格式、测试 | `uv run ruff check .` `uv run ruff format --check .` `uv run python -m pytest` | 全部通过，0 failed |
| **G3** 构建 | wheel / sdist 可生成 | `uv build` | `dist/` 下同时有 `.whl` 与 `.tar.gz` |
| **G4** 产物内容 | 包文件齐全、入口与类型标记正确 | `uv run python -m zipfile -l dist/ssstool-*.whl` | 含 `ssstool/__init__.py`、`ssstool/py.typed`、`*.dist-info/entry_points.txt` |
| **G5** 安装冒烟 | 干净 venv 装 wheel 与 sdist 都能跑 | 见下方脚本 | `ssstool --version`、`ssstool doctor` 退出码 0 |
| **G6** 元数据渲染 | README 能被 PyPI 正确渲染、元数据无畸形 | `uvx twine check dist/*` | `PASSED`（需网络，首次会下载 twine） |
| **G7** 上传预演（可选，需凭据） | 文件名/大小/端点无问题 | `uv publish --dry-run --publish-url https://upload.pypi.org/legacy/` | 有凭据时打印将上传的文件并退出 0。**本地无凭据时会报 `Trusted publishing failed`，这是预期行为**，此时以 G6 + 文件名规范检查替代 |

G5 冒烟脚本（Windows PowerShell；Linux/macOS 把 `Scripts` 换成 `bin`、`ssstool.exe` 换成 `ssstool`）：

```powershell
uv venv .smoke --python 3.12
uv pip install --python .smoke\Scripts\python.exe dist/ssstool-0.1.0-py3-none-any.whl
.smoke\Scripts\ssstool.exe --version
.smoke\Scripts\ssstool.exe doctor
uv pip install --python .smoke\Scripts\python.exe --force-reinstall dist/ssstool-0.1.0.tar.gz
.smoke\Scripts\ssstool.exe --version
Remove-Item -Recurse -Force .smoke
```

---

## 4. 逐步操作

### Step 1 · 同步 main

```powershell
git switch main
git pull --ff-only
git status --short          # 必须干净
```

### Step 2 · 定版本号

```powershell
uv version --bump minor     # 按第 2 节选 patch/minor/major
uv version --short
```

### Step 3 · 补台账与文档

- `docs/LEDGER.md`：插入本版本记录（状态写「未发布」），索引表加一行。
- `docs/capabilities/README.md`：新增/变更能力登记。
- 对应能力文档、`README.md` 能力表同步。
- 若有`BREAKING`，在台账写明升级步骤。

### Step 4 · 跑全部门禁

按第 3 节 G2 → G6 顺序执行，把真实输出贴进台账「验证证据」。

### Step 5 · 提交并合并

```powershell
git add -A
git commit -m "chore(release): prepare v0.2.0"
git push origin main
```

### Step 6 ·（首次或大改）TestPyPI 演练

```powershell
git tag v0.2.0rc1
git push origin v0.2.0rc1
```

工作流路由到 TestPyPI 后验证：

```powershell
uvx --index-url https://test.pypi.org/simple/ --from ssstool==0.2.0rc1 ssstool --version
```

### Step 7 · 打正式 tag

```powershell
git tag v0.2.0
git push origin v0.2.0
```

CI 会：校验 tag 与 `pyproject.toml` 版本一致 → 构建 → 上传 PyPI（Trusted Publishing，无 token）。

### Step 8 · 发布后验证（必须做）

```powershell
# 1) PyPI 能查到该版本
Invoke-RestMethod https://pypi.org/pypi/ssstool/0.2.0/json | Select-Object -ExpandProperty info

# 2) 陌生环境能装、能跑
uvx --refresh --from ssstool==0.2.0 ssstool --version

# 3) 本地 wheel 与 PyPI 上的文件哈希一致（证明传的就是构建的那个）
(Get-FileHash dist/ssstool-0.2.0-py3-none-any.whl -Algorithm SHA256).Hash.ToLower()
(Invoke-RestMethod https://pypi.org/pypi/ssstool/0.2.0/json).urls | ForEach-Object { "$($_.filename) $($_.digests.sha256)" }
```

### Step 9 · 收尾

- 台账状态改为「已发布（YYYY-MM-DD）」。
- GitHub Release 写变更摘要（可从台账记录直接改写）。
- 若本次有 `BREAKING`，在 Release 里单独标注升级方法。

---

## 5. 首次发布特别注意

1. **项目在 PyPI 上还不存在** → 必须用 *pending trusted publisher*（第 1 节第 3 条），不能先建项目再配。
2. 首次发布后，pending publisher 会自动转为正式 publisher 并绑定项目。
3. 首次发布前，`README.md` 里的 `pip install ssstool` 只是预期命令；发布成功后才成立（台账与 README 的「发布状态」要同步更新）。
4. 许可证未定会导致 PyPI 页面无 license 信息，且用户在法律上无权使用——**这是首发硬门禁**。

---

## 6. 回滚与 yank

| 情况 | 做法 | 注意 |
| --- | --- | --- |
| 刚发布就发现严重缺陷 | 发 patch 版本修复，这是首选 | 不要试图删文件重传 |
| 版本会误导用户（如误发实验代码） | 在 PyPI 该版本页面执行 **Yank release**，台账标「已撤回」并写明原因 | Yank 后默认安装不会选中它，但精确 `==` 仍可安装；文件仍存在 |
| 需要彻底删除 | 仅限合规/安全事件，走 PyPI 支持流程 | 删除后**该版本号永久不可再用** |
| CI 上传失败但版本已占用 | 只能升版本号重发 | 不要改 tag 复用旧版本号 |

---

## 7. 故障排查

| 报错 | 根因 | 处理 |
| --- | --- | --- |
| `403 Invalid or non-existent authentication information` | Trusted Publisher 的 Owner/Repo/Workflow/Environment 与实际不符 | 逐字核对第 1 节第 3 条四个字段，注意大小写与文件名 |
| `400 File already exists` | 同版本已上传过 | 升版本号，不允许覆盖 |
| `invalid value for 'requires-python'` | 语法或版本范围写错 | 用 `>=3.10` 这类合法说明符 |
| PyPI 页面 README 显示为源码 | `readme` 指向错误或内容类型不对 | `[project].readme = "README.md"`，跑 G6 `twine check` |
| `Metadata is missing required fields` | 描述/名称/版本缺失或非法 | 检查 `name`、`version`、`description` |
| 用户装完 `ssstool: command not found` | 安装到了非 PATH 的 Scripts 目录，或用了 3.7 解释器 | `python -m ssstool --version` 自检；确认 `>=3.10` |
| `ERROR_OPEN_FAILED`（Windows，uv 建 `.exe`） | uv trampoline 偶发失败 | 用 `uv run python -m pytest`；重试 `uv sync` |
| 安装后 `doctor` 中文乱码 | 终端编码（本项目 CLI 已全 ASCII，出现即说明跑的是旧版本） | `ssstool --version` 确认版本 |

---

## 8. 发布检查清单（复制到 PR 描述）

```markdown
- [ ] G0 配置就绪（Trusted Publisher / Environment / 许可证 / 作者信息）
- [ ] 版本号 = pyproject.toml，且台账已插入本版本记录（状态：未发布）
- [ ] 能力登记表与 README 能力表一致
- [ ] ruff check / ruff format --check / pytest 全绿
- [ ] uv build 产物含 wheel + sdist
- [ ] wheel 含 py.typed 与 entry_points.txt
- [ ] 干净 venv 安装 wheel 后 `ssstool --version`、`ssstool doctor` 退出码 0
- [ ] 干净 venv 安装 sdist 后同样可运行
- [ ] twine check 通过
- [ ] `uv publish --dry-run` 无异常
- [ ] tag 格式 vX.Y.Z，与版本号一致
- [ ] 发布后 uvx 安装验证 + 哈希比对完成
- [ ] 台账状态已改为「已发布」，GitHub Release 已写
```
