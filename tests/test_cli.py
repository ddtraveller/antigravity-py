"""CLI-level tests using Click's runner with subprocess mocked."""

import sys

import pytest
from click.testing import CliRunner

from agy_py import cli as cli_mod
from agy_py import core


class FakeProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def fake_binary(tmp_path, monkeypatch):
    name = "agy.exe" if sys.platform == "win32" else "agy"
    binary = tmp_path / name
    binary.write_text("")
    monkeypatch.setenv(core.BINARY_ENV_VAR, str(binary))
    return str(binary)


def test_run_propagates_exit_code(fake_binary, monkeypatch):
    monkeypatch.setattr(core.subprocess, "run",
                        lambda argv, **kw: FakeProc(3, "agent output", ""))
    result = CliRunner().invoke(cli_mod.cli, ["run", "hi"])
    assert result.exit_code == 3
    assert "agent output" in result.output


def test_run_outputs_stdout(fake_binary, monkeypatch):
    monkeypatch.setattr(core.subprocess, "run",
                        lambda argv, **kw: FakeProc(0, "agent says hi", ""))
    result = CliRunner().invoke(cli_mod.cli, ["run", "q"])
    assert result.exit_code == 0
    assert "agent says hi" in result.output


def test_doctor_errors_when_binary_missing(tmp_path, monkeypatch):
    monkeypatch.delenv(core.BINARY_ENV_VAR, raising=False)
    monkeypatch.setattr(core.shutil, "which", lambda *_: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(core.Path, "home", lambda: tmp_path)
    result = CliRunner().invoke(cli_mod.cli, ["doctor"])
    assert result.exit_code == core.EXIT_ERROR
    assert "NOT FOUND" in result.output


def test_config_set_and_get(tmp_path, monkeypatch):
    monkeypatch.setattr(core.Path, "home", lambda: tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli_mod.cli, ["config", "set", "verbosity", "low"]).exit_code == 0
    got = runner.invoke(cli_mod.cli, ["config", "get", "verbosity"])
    assert got.exit_code == 0
    assert "low" in got.output
