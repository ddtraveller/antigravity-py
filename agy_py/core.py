"""Dependency-free wrapper around the Antigravity ``agy`` CLI binary.

Everything here is plain ``subprocess``/``json``/``shutil`` so it can be unit
tested by mocking :func:`subprocess.run` without ``agy`` actually installed.

Flag provenance (verified against agy v1.0.2 on Windows, 2026-05-26)
-------------------------------------------------------------------
Confirmed by running ``agy --help``: the print/command mode ``-p`` (alias for
``--print`` -- "run a single prompt non-interactively and print the response"),
plus ``--sandbox``, ``--dangerously-skip-permissions``, ``-c`` / ``--continue``,
``--conversation``, ``--add-dir``, and the subcommands ``update``,
``changelog`` and ``plugin``. The Windows binary installs to
``%LOCALAPPDATA%\\agy\\bin\\agy.exe``.

The earlier third-party-attested ``--output-format json`` and ``-m <model>``
flags do NOT exist in agy v1.0.2 and have been removed. ``settings.json`` lives
at ``~/.gemini/antigravity-cli/settings.json`` per the official docs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

# Exit codes (mirrors notebooklm-py's contract).
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_TIMEOUT = 2

# --- agy argument names (verified via `agy --help`, v1.0.2) ---
FLAG_PRINT = "-p"  # alias for --print: run a single prompt non-interactively
FLAG_SANDBOX = "--sandbox"
FLAG_SKIP_PERMISSIONS = "--dangerously-skip-permissions"
FLAG_CONTINUE = "--continue"
FLAG_CONVERSATION = "--conversation"
FLAG_ADD_DIR = "--add-dir"

BINARY_ENV_VAR = "AGY_BINARY"


class AgyError(Exception):
    """Raised for any wrapper-level failure; carries a process exit code."""

    def __init__(self, message: str, exit_code: int = EXIT_ERROR):
        super().__init__(message)
        self.exit_code = exit_code


def _default_binaries() -> list[str]:
    """Platform default install locations for the ``agy`` binary."""
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            return []
        return [
            str(Path(local) / "agy" / "bin" / "agy.exe"),  # actual (agy v1.0.2)
            str(Path(local) / "Antigravity" / "agy.exe"),  # per docs (fallback)
        ]
    return [str(Path.home() / ".local" / "bin" / "agy")]


def find_binary(explicit: str | None = None) -> str:
    """Locate the ``agy`` executable.

    Search order: ``explicit`` argument, ``$AGY_BINARY``, ``PATH``, then the
    platform's default install location (``%LOCALAPPDATA%\\agy\\bin\\agy.exe`` on
    Windows, ``~/.local/bin/agy`` elsewhere). Raises :class:`AgyError` if nothing
    is found.
    """
    candidates: list[str | None] = [explicit, os.environ.get(BINARY_ENV_VAR)]
    candidates.append(shutil.which("agy"))
    candidates.extend(_default_binaries())

    for candidate in candidates:
        if not candidate:
            continue
        if Path(candidate).exists():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    raise AgyError(
        "Could not find the `agy` binary. Install it with "
        "`irm https://antigravity.google/cli/install.ps1 | iex` (Windows) or "
        "`curl -fsSL https://antigravity.google/cli/install.sh | bash` (mac/Linux), "
        f"or point ${BINARY_ENV_VAR} at the executable.",
        EXIT_ERROR,
    )


@dataclass
class Result:
    """Outcome of an ``agy`` invocation."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def json(self) -> Any:
        """Parse ``stdout`` as JSON, raising :class:`AgyError` on bad output."""
        try:
            return json.loads(self.stdout)
        except json.JSONDecodeError as exc:
            raise AgyError(
                f"`agy` did not return valid JSON: {exc}. Raw output:\n{self.stdout}",
                EXIT_ERROR,
            ) from exc


# --- Config file locations -------------------------------------------------
# settings.json is confirmed by the official docs. The MCP / hooks paths are
# best-effort (third-party synthesis) and may need correction.

def settings_path() -> Path:
    return Path.home() / ".gemini" / "antigravity-cli" / "settings.json"


def keybindings_path() -> Path:
    return Path.home() / ".gemini" / "antigravity-cli" / "keybindings.json"


def mcp_config_path() -> Path:  # best-effort
    return Path.home() / ".gemini" / "config" / "mcp_config.json"


def hooks_path() -> Path:  # best-effort
    return Path.home() / ".gemini" / "config" / "hooks.json"


class AgyRunner:
    """Runs the ``agy`` binary and returns :class:`Result` objects."""

    def __init__(self, binary: str | None = None):
        self.binary = find_binary(binary)

    def _run(self, args: Iterable[str], timeout: float | None = None) -> Result:
        argv = [self.binary, *args]
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,  # stdin stays inherited so pipes pass through
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise AgyError(f"`agy` timed out after {timeout}s.", EXIT_TIMEOUT) from exc
        except OSError as exc:
            raise AgyError(f"Failed to execute `{self.binary}`: {exc}.", EXIT_ERROR) from exc
        return Result(proc.returncode, proc.stdout or "", proc.stderr or "")

    # -- simple pass-through commands --
    def version(self) -> Result:
        return self._run(["--version"])

    def update(self) -> Result:
        return self._run(["update"])

    def changelog(self) -> Result:
        return self._run(["changelog"])

    def plugin(self, args: Iterable[str]) -> Result:
        return self._run(["plugin", *list(args)])

    def raw(self, args: Iterable[str], timeout: float | None = None) -> Result:
        """Escape hatch: pass arbitrary arguments straight to ``agy``."""
        return self._run(list(args), timeout=timeout)

    # -- print / command mode (agy -p) --
    def prompt(
        self,
        text: str,
        *,
        sandbox: bool = False,
        skip_permissions: bool = False,
        continue_last: bool = False,
        conversation: str | None = None,
        add_dirs: Iterable[str] | None = None,
        timeout: float | None = None,
        extra_args: Iterable[str] | None = None,
    ) -> Result:
        """Run ``agy -p "<text>"`` (non-interactive print mode) and capture output."""
        args: list[str] = [FLAG_PRINT, text]
        if continue_last:
            args.append(FLAG_CONTINUE)
        if conversation:
            args += [FLAG_CONVERSATION, conversation]
        for directory in add_dirs or []:
            args += [FLAG_ADD_DIR, directory]
        if sandbox:
            args.append(FLAG_SANDBOX)
        if skip_permissions:
            args.append(FLAG_SKIP_PERMISSIONS)
        if extra_args:
            args += list(extra_args)
        return self._run(args, timeout=timeout)


def diagnostics(binary: str | None = None) -> dict[str, Any]:
    """Collect environment health info (used by the ``doctor`` command)."""
    info: dict[str, Any] = {}
    try:
        resolved = find_binary(binary)
        info["binary"] = resolved
        info["binary_found"] = True
    except AgyError as exc:
        info["binary"] = None
        info["binary_found"] = False
        info["binary_error"] = str(exc)

    info["settings_path"] = str(settings_path())
    info["settings_exists"] = settings_path().exists()
    info["gemini_dir"] = str(Path.home() / ".gemini" / "antigravity")
    info["gemini_dir_exists"] = (Path.home() / ".gemini" / "antigravity").exists()
    return info


# --- settings.json read/write (dotted-key access) --------------------------

def load_settings() -> dict[str, Any]:
    path = settings_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise AgyError(f"settings.json is not valid JSON: {exc}.", EXIT_ERROR) from exc


def get_setting(key: str | None = None) -> Any:
    data = load_settings()
    if not key:
        return data
    cursor: Any = data
    for part in key.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            raise AgyError(f"Setting '{key}' not found.", EXIT_ERROR)
        cursor = cursor[part]
    return cursor


def set_setting(key: str, value: Any) -> dict[str, Any]:
    data = load_settings()
    cursor = data
    parts = key.split(".")
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
        if not isinstance(cursor, dict):
            raise AgyError(f"Cannot set '{key}': '{part}' is not an object.", EXIT_ERROR)
    cursor[parts[-1]] = value
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data
