# 能力：环境自检（core.doctor）

| 字段 | 值 |
| --- | --- |
| 能力 ID | `core.doctor` |
| 状态 | 可用 |
| 引入版本 | 0.1.0 |
| 入口 | `ssstool doctor` |

## 能干什么

一条命令回答三个问题：**装的哪一版、跑在哪个解释器上、包在哪里**。用于装完自检，以及用户报「跑不起来」时一键收集环境事实，省掉来回追问。

## 怎么用

```console
$ ssstool doctor
ssstool     : 0.1.0
python      : 3.12.13 (CPython)
executable  : D:\new_job\git_code\ssstool\.venv\Scripts\python.exe
platform    : Windows-11-10.0.26200-SP0
package path: D:\new_job\git_code\ssstool\src\ssstool
status      : ok
```

字段含义：

| 字段 | 含义 | 怎么用 |
| --- | --- | --- |
| `ssstool` | 包版本 | 与 `pip show ssstool` 对照 |
| `python` | 解释器版本与实现 | 低于 3.10 即不受支持 |
| `executable` | 当前 Python 可执行文件路径 | 判断是否装到了非预期的解释器/虚拟环境 |
| `platform` | 操作系统与架构 | 报障时提供 |
| `package path` | 包实际加载路径 | 出现 `src/ssstool` 说明是 editable（源码）安装；出现 `site-packages` 说明是正常安装 |
| `status` | 固定 `ok` | 仅表示命令本身执行成功，不代表环境「健康」 |

## 行为与退出码

| 场景 | 行为 | 退出码 |
| --- | --- | --- |
| 正常执行 | 6 行信息输出到 stdout | 0 |
| 未知子命令/参数 | argparse 报错到 stderr | 2 |

## 边界与限制

- **只读**：不写文件、不改配置、不装依赖。
- **不联网**：不检查 PyPI 新版本、不探测网络。
- **不做健康判断**：`status: ok` 只说明自检命令跑通了，不保证你的业务代码能跑。
- 输出包含本机路径，贴到公开 issue 前自行脱敏。
- 输出格式不是稳定 API（列对齐可能调整），**不要**用 `awk`/正则解析它做自动化；需要版本请用 `ssstool --version`。

## 排障

| 现象 | 判断 | 处理 |
| --- | --- | --- |
| `executable` 指向 Python 3.7 | 装到了系统解释器 | 用 `uv` 或对应 venv 重装 |
| `package path` 是 `src/ssstool` | editable 安装，改源码即时生效 | 正常，发布验证请用 wheel 安装 |
| 输出含 `���` | 跑的是 0.1.0 之前的旧构建（CLI 已全 ASCII） | `ssstool --version` 确认并升级 |
| `command not found` | Scripts 目录不在 PATH | `python -m ssstool doctor` 兜底 |

## 实现位置

| 文件 | 作用 |
| --- | --- |
| `src/ssstool/cli.py` `_doctor_lines()` | 采集并格式化环境信息 |
| `src/ssstool/cli.py` `_cmd_doctor()` | 输出并返回退出码 |
| `src/ssstool/cli.py` `build_parser()` | 注册 `doctor` 子命令 |

## 验证

`tests/test_cli.py`：

- `test_doctor_reports_environment`（版本、python、ok 字段齐全）
- `test_no_arguments_prints_help`（子命令可被发现）

## 变更历史

- 0.1.0：随包骨架引入（见台账 v0.1.0）。
