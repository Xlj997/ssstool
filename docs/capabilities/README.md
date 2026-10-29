# 能力登记表

> 本表是 **ssstool 能干什么的唯一清单**。README、发布说明、对外介绍都必须与这里一致；表里没有的，就是不存在。

## 登记表

| ID | 能力 | 入口 | 状态 | 引入版本 | 文档 |
| --- | --- | --- | --- | --- | --- |
| `core.version` | 版本查询：当前安装的是哪一版 | `ssstool --version`、`python -m ssstool --version`、`ssstool.__version__`、`ssstool.get_version()` | 可用 | 0.1.0 | [version.md](version.md) |
| `core.doctor` | 环境自检：包版本、Python、解释器路径、平台 | `ssstool doctor` | 可用 | 0.1.0 | [doctor.md](doctor.md) |
| `browser.open` | 打开一个受控 Chrome 实例并暴露 CDP 端点（Windows） | `ssstool browser open [--port 9222] [--profile temp\|default]` | 可用 | 0.2.0 | [browser.md](browser.md) |
| `browser.hardening` | 无认证代理 + 反检测启动参数（WebRTC/QUIC/DNS 预取硬化） | `ssstool browser open --proxy <url> [--proxy-bypass <list>] [--stealth]` | 可用 | 0.2.0 | [browser.md](browser.md) |
| `browser.close` | 关闭 ssstool 启动的 Chrome，释放端口并删除临时 profile | `ssstool browser close [--port 9222]` | 可用 | 0.2.0 | [browser.md](browser.md) |
| `browser.profile` | 探测真实 Chrome 用户配置目录（策略/运行态/快捷方式/标准路径） | `ssstool browser profile [--json]` | 可用 | 0.2.0 | [browser.md](browser.md) |

## 状态词典

| 状态 | 含义 | 对外可宣称？ |
| --- | --- | --- |
| 可用 | 已实现、有测试、有文档、已随某个版本发布或在 `main` 上可用 | 是（需注明版本） |
| 开发中 | 代码在写，接口可能变，未进任何发布版本 | 否 |
| 提案 | 只在候选池里，尚未排期 | 否 |
| 已弃用 | 仍能用但计划移除，文档必须写替代方案与移除版本 | 只能说「已弃用」 |

## 候选池（全部**未实现**，不构成承诺）

以下只是方向占位，**没有一行代码**，不得对外宣传。确认要做时，必须先在登记表登记并走下面的流程。

| 想法 | 可能的入口 | 待确认的问题 |
| --- | --- | --- |
| 文本/文件摘要 | `ssstool hash <path|->` | 算法集合？流式处理？ |
| JSON 格式化与校验 | `ssstool json <file>` | 是否要保留键顺序？错误信息格式？ |
| 时间戳互转 | `ssstool ts <value>` | 时区默认值？本地还是 UTC？ |

## 新增能力流程（顺序不可颠倒）

1. **登记**：在登记表加一行，状态写「开发中」，并创建 `docs/capabilities/<英文短名>.md`（从 `_TEMPLATE.md` 复制）。
2. **实现**：在 `src/ssstool/` 落地；CLI 能力在 `cli.py` 注册 handler。
3. **测试**：成功路径 ≥1 条、失败/边界路径 ≥1 条，离线可跑。
4. **更新文档**：能力文档补用法、参数、输出、退出码、边界、实现位置。
5. **写台账**：`docs/LEDGER.md` 记录原因、变更文件、验证证据；发布后状态改「已发布」并填版本号。

## 能力文档四问（写不清就是没想清）

1. **能干什么**：一句话说清解决的问题，不写「强大的」「优雅的」。
2. **怎么用**：可复制的命令/代码 + 真实输出。
3. **边界在哪**：不做什么、什么情况下会失败、失败时退出码与提示是什么。
4. **怎么验证**：对应的测试名或自检命令，让人能自己确认。

## 命名约定

- 能力 ID 用 `域.短名`：`core.*` 为包自身能力，后续按功能域扩展（如 `text.*`、`fs.*`）。
- 子命令名用小写单词，不加前缀、不用缩写（`doctor` 而不是 `doc`）。
- 文档文件名 = 子命令名或公共函数名，全小写，必要时用连字符。
