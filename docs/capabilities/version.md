# 能力：版本查询（core.version）

| 字段 | 值 |
| --- | --- |
| 能力 ID | `core.version` |
| 状态 | 可用 |
| 引入版本 | 0.1.0 |
| 入口 | `ssstool --version`、`python -m ssstool --version`、`ssstool.__version__`、`ssstool.get_version()` |

## 能干什么

确认「当前这个环境里装的 ssstool 到底是哪一版」。用于：装完自检、排查「代码没生效」、在脚本里做版本门槛判断。

## 怎么用

命令行：

```console
$ ssstool --version
ssstool 0.1.0

$ python -m ssstool --version
ssstool 0.1.0
```

库：

```python
import ssstool

print(ssstool.__version__)  # 0.1.0
print(ssstool.get_version())  # 0.1.0，等价
```

版本门槛判断：

```python
import ssstool

if tuple(int(p) for p in ssstool.__version__.split(".")[:2]) < (0, 2):
    raise SystemExit("ssstool >= 0.2 required")
```

## 行为与退出码

| 场景 | 输出 | 退出码 |
| --- | --- | --- |
| `--version` / `-V` | `ssstool <version>` | 0 |
| `python -m ssstool --version` | 同上 | 0 |
| 未安装，直接跑源码 | `0.0.0+source` | 0 |

## 边界与限制

- **不联网**：不会检查 PyPI 上是否有更新版本。要知道最新版，请自行查询 `https://pypi.org/pypi/ssstool/json`。
- **不支持环境变量覆盖**：版本只来自包元数据，故意不提供「伪装版本」的开关。
- 未安装源码态返回 `0.0.0+source`（PEP 440 合法本地版本），含义是「这不是安装态，别拿它做发布判断」。
- 版本号格式由 `pyproject.toml` 决定，本项目遵循 SemVer；预发布版本形如 `0.2.0rc1`。

## 排障

版本与预期不一致时，先确认装了几份、装的哪份：

```console
$ pip show ssstool
$ python -c "import ssstool, sys; print(ssstool.__file__); print(sys.executable)"
```

`ssstool doctor` 会同时打印版本、解释器路径与包路径，比 `pip show` 更快定位「装到了另一个解释器」的问题。

## 实现位置

| 文件 | 作用 |
| --- | --- |
| `pyproject.toml` `[project].version` | 唯一版本源 |
| `src/ssstool/_version.py` `get_version()` | 从安装元数据读取版本，未安装时兜底 |
| `src/ssstool/__init__.py` | 导出 `__version__` / `get_version` |
| `src/ssstool/cli.py` `build_parser()` | 注册 `-V/--version` |

## 验证

`tests/test_cli.py`：

- `test_version_is_pep440_ish`
- `test_get_version_matches_dunder`
- `test_version_flag_exits_zero`
- `test_module_entry_point_runs`

## 变更历史

- 0.1.0：随包骨架引入（见台账 v0.1.0）。
