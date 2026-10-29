"""ssstool 的冒烟级回归测试：版本、CLI 契约、打包标记。"""

from __future__ import annotations

import re
import subprocess
import sys
from importlib import resources

import pytest

import ssstool
from ssstool.cli import main


def test_version_is_pep440_ish() -> None:
    assert re.match(r"^\d+\.\d+\.\d+([.\-+].*)?$", ssstool.__version__)


def test_get_version_matches_dunder() -> None:
    assert ssstool.get_version() == ssstool.__version__


def test_version_flag_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert ssstool.__version__ in out
    assert "ssstool" in out


def test_no_arguments_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "doctor" in out


def test_doctor_reports_environment(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert ssstool.__version__ in out
    assert "python" in out
    assert "ok" in out


def test_module_entry_point_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ssstool", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert ssstool.__version__ in result.stdout


def test_py_typed_marker_is_shipped() -> None:
    assert resources.files("ssstool").joinpath("py.typed").is_file()
