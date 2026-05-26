"""Unit tests for agy_py.core. These mock subprocess so they pass even when
the real `agy` binary is not installed."""

import json
import subprocess
import sys

import pytest

from agy_py import core
from agy_py.core import AgyError, AgyRunner


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


# --- find_binary -----------------------------------------------------------

def test_find_binary_explicit(tmp_path):
    p = tmp_path / "agy"
    p.write_text("")
    assert core.find_binary(str(p)) == str(p)


def test_find_binary_env(fake_binary):
    assert core.find_binary() == fake_binary


def test_find_binary_missing(tmp_path, monkeypatch):
    monkeypatch.delenv(core.BINARY_ENV_VAR, raising=False)
    monkeypatch.setattr(core.shutil, "which", lambda *_: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))  # win default -> nonexistent
    monkeypatch.setattr(core.Path, "home", lambda: tmp_path)  # unix default -> nonexistent
    with pytest.raises(AgyError) as excinfo:
        core.find_binary()
    assert excinfo.value.exit_code == core.EXIT_ERROR


# --- prompt / argv construction --------------------------------------------

def test_prompt_builds_argv(fake_binary, monkeypatch):
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return FakeProc(0, "done", "")

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    AgyRunner().prompt(
        "hello",
        continue_last=True,
        conversation="abc123",
        add_dirs=["src", "tests"],
        sandbox=True,
        skip_permissions=True,
    )
    assert captured["argv"][0] == fake_binary
    assert captured["argv"][1:] == [
        "-p", "hello",
        "--continue",
        "--conversation", "abc123",
        "--add-dir", "src",
        "--add-dir", "tests",
        "--sandbox",
        "--dangerously-skip-permissions",
    ]
    # stdin is left inherited so shell pipes flow through to agy.
    assert captured["kwargs"]["capture_output"] is True
    assert "stdin" not in captured["kwargs"]


def test_prompt_minimal_argv(fake_binary, monkeypatch):
    captured = {}
    monkeypatch.setattr(core.subprocess, "run",
                        lambda argv, **kw: captured.update(argv=argv) or FakeProc(0, "hi", ""))
    AgyRunner().prompt("just text")
    assert captured["argv"][1:] == ["-p", "just text"]


def test_result_json_helpers():
    assert core.Result(0, '{"a": 1}', "").json() == {"a": 1}
    with pytest.raises(AgyError):
        core.Result(0, "not json", "").json()


def test_timeout_maps_to_exit_2(fake_binary, monkeypatch):
    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs.get("timeout"))

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    with pytest.raises(AgyError) as excinfo:
        AgyRunner().prompt("x", timeout=1)
    assert excinfo.value.exit_code == core.EXIT_TIMEOUT


def test_version_passthrough(fake_binary, monkeypatch):
    monkeypatch.setattr(core.subprocess, "run",
                        lambda argv, **kw: FakeProc(0, "agy 2.0.0", ""))
    result = AgyRunner().version()
    assert result.ok
    assert "2.0.0" in result.stdout


# --- settings.json read/write ----------------------------------------------

def test_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(core.Path, "home", lambda: tmp_path)
    core.set_setting("theme", "dark")
    core.set_setting("editor.tabSize", 2)
    assert core.get_setting("theme") == "dark"
    assert core.get_setting("editor.tabSize") == 2
    assert core.get_setting() == {"theme": "dark", "editor": {"tabSize": 2}}
    expected = tmp_path / ".gemini" / "antigravity-cli" / "settings.json"
    assert core.settings_path() == expected
    assert json.loads(expected.read_text())["editor"]["tabSize"] == 2


def test_get_missing_setting_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(core.Path, "home", lambda: tmp_path)
    with pytest.raises(AgyError):
        core.get_setting("does.not.exist")
