# agy-py — Python wrapper for the Google Antigravity `agy` CLI

> **Drive Google Antigravity's `agy` terminal coding agent from Python and the shell** — non-interactive (print-mode) prompts, conversation control, scripting, and CI/CD automation, with a clean `subprocess`-based core and a Click command-line interface.

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Tested with agy v1.0.2](https://img.shields.io/badge/tested%20with-agy%20v1.0.2-blue.svg)
![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)
![Google Antigravity: unofficial wrapper](https://img.shields.io/badge/Google%20Antigravity-unofficial%20wrapper-lightgrey.svg)

`agy-py` is a small, dependency-light **Python wrapper around the Google
Antigravity CLI** — the `agy` binary that ships with **Antigravity 2.0**
(announced at Google I/O 2026). It lets you run Antigravity's AI coding agent
**non-interactively** — one-shot prompts via `agy -p` (print mode), conversation
continuation, workspace directories, and predictable exit codes — so you can
call the agent from Python programs, shell scripts, Git hooks, and CI/CD
pipelines instead of the interactive terminal UI.

It does **not** reimplement the agent. It wraps the official `agy` binary and
gives you a tidy, testable surface — modeled on the structure of
[`notebooklm-py`](https://github.com/teng-lin/notebooklm-py): a pure-stdlib core
plus a thin CLI, with a stable `0 / 1 / 2` exit-code contract.

> **Unofficial.** Not affiliated with, endorsed by, or supported by Google.
> "Antigravity", "Google Antigravity", and "Gemini" are trademarks of Google LLC.
> The wrapped command surface was **verified against `agy` v1.0.2**; see
> [Command surface & verification status](#command-surface--verification-status).

---

## Table of contents

- [Why agy-py?](#why-agy-py)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Command reference](#command-reference)
- [Headless usage, scripting & CI/CD](#headless-usage-scripting--cicd)
- [Python API](#python-api)
- [Configuration](#configuration)
- [Exit codes](#exit-codes)
- [Command surface & verification status](#command-surface--verification-status)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [agy-py vs. calling agy directly](#agy-py-vs-calling-agy-directly)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Related projects & references](#related-projects--references)

---

## Why agy-py?

The `agy` CLI is **terminal-UI-first**: most of its power lives in an interactive
session (slash commands like `/goal`, `/plan`, `/schedule`). That's great for a
human at a keyboard, but awkward to **automate**. `agy-py` focuses on the
scriptable parts and smooths the rough edges:

- **Non-interactive by default** — wraps `agy -p "<prompt>"` (print mode) so a
  single prompt runs and exits, perfect for scripts.
- **Robust binary discovery** — finds `agy` on `PATH`, via `$AGY_BINARY`, or at
  the platform's real install path; one clear error if it can't.
- **Predictable failures** — every error is a clean stderr message plus a
  documented exit code (no stack traces in your pipeline), with a `--timeout`
  hard-kill that returns exit code 2.
- **Conversation control** — `--continue` / `--conversation` to resume sessions.
- **Importable** — `from agy_py import AgyRunner` to call the agent from Python.
- **Tested without the binary** — the core mocks `subprocess`, so `pytest` is
  green even on machines where `agy` isn't installed.

## Features

| Capability | How |
|------------|-----|
| Run one-shot prompts (non-interactive) | `agy-py run "..."` → `agy -p "..."` |
| Continue / resume a conversation | `--continue`, `--conversation <id>` |
| Add workspace directories | `--add-dir <path>` (repeatable) |
| Sandbox / skip-permission overrides | `--sandbox`, `--skip-permissions` |
| Pipe data into the agent | `cat file | agy-py run "..."` (stdin forwarded) |
| Timeout long runs | `--timeout SECONDS` (exit code 2) |
| Check install & config health | `agy-py doctor` (with `--json`) |
| Workspace-trust check / fix | `agy-py doctor`, `run --trust`, `config trust` |
| Read/write `settings.json` | `agy-py config get/set/path` |
| Manage plugins / view changelog | `agy-py plugin ...`, `agy-py changelog` |
| Update / version | `agy-py update`, `agy-py version` |
| Raw escape hatch (forwards everything) | `agy-py raw <anything>` |
| Use as a Python library | `from agy_py import AgyRunner` |

## Requirements

- **Python 3.9+**
- The **`agy` binary** (Google Antigravity CLI) — tested against **v1.0.2**.
- Works on **Windows, macOS, and Linux**.

## Installation

### 1. Install `agy-py`

```bash
pip install -e .            # from a clone of this repo
# or, with test/dev tools:
pip install -e ".[dev]"
```

The only runtime dependency is [`click`](https://click.palletsprojects.com/).

### 2. Install the `agy` binary

```powershell
# Windows (PowerShell) → installs to %LOCALAPPDATA%\agy\bin\agy.exe
irm https://antigravity.google/cli/install.ps1 | iex
```
```bash
# macOS / Linux → installs to ~/.local/bin/agy
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

On first **real** use, `agy` authenticates via your OS keyring or a browser
Google Sign-In — run `agy` once interactively to sign in. Then verify:

```bash
agy-py doctor
```

### Binary discovery order

`agy-py` locates the executable in this order:

1. `--binary /path/to/agy`
2. `$AGY_BINARY` environment variable
3. `agy` on your `PATH`
4. Platform default: `%LOCALAPPDATA%\agy\bin\agy.exe` (Windows) or
   `~/.local/bin/agy` (macOS/Linux)

If none resolve, every command fails fast with an actionable message (exit 1).

## Quickstart

```bash
agy-py doctor                          # agy installed? folder trusted? config paths?
agy-py version                         # agy --version  → e.g. 1.0.2
agy-py run "Write a Python hello world" --trust   # --trust: agy -p hangs in untrusted folders
agy-py run "Add docstrings" --add-dir ./src --sandbox
cat error.log | agy-py run "Explain the root cause of this stack trace"
agy-py run "And now add type hints" --continue   # resume the last conversation
```

## Command reference

| Command | Wraps / does | Key options |
|---------|--------------|-------------|
| `agy-py run "PROMPT"` | `agy -p "PROMPT"` (print mode; renders to your terminal) | `-c/--continue`, `--conversation`, `--add-dir`, `--sandbox`, `--skip-permissions`, `--trust`, `--timeout`, `--binary` |
| `agy-py version` | `agy --version` | `--binary` |
| `agy-py update` | `agy update` | `--binary` |
| `agy-py changelog` | `agy changelog` (release notes) | `--binary` |
| `agy-py plugin ARGS…` | `agy plugin …` (list/install/enable/…) | (uses `$AGY_BINARY`/`PATH`) |
| `agy-py raw ARGS…` | passes `ARGS` straight to `agy` (incl. `--help`) | (uses `$AGY_BINARY`/`PATH`) |
| `agy-py doctor` | checks binary + config locations | `--json`, `--binary` |
| `agy-py auth info\|login\|logout` | describes the keyring/browser auth model | — |
| `agy-py config path` | prints `settings.json` location | — |
| `agy-py config get [KEY]` | reads all settings or a dotted `KEY` | `--json` |
| `agy-py config set KEY VALUE` | writes a dotted `KEY` (`VALUE` parsed as JSON) | — |
| `agy-py config trust [PATH]` | add `PATH` (default cwd) to `trustedWorkspaces` | — |
| `agy-py config mcp-path` / `hooks-path` | prints MCP / hooks config paths (best-effort) | — |

Run `agy-py --help` or `agy-py <command> --help` for full details.

## Headless usage, scripting & CI/CD

`agy-py run` is built for non-interactive use. Stdin is **forwarded** to `agy`,
so shell pipelines work as expected.

**Pipe a file in as context:**
```bash
cat sales.csv | agy-py run "Summarize this data and flag anomalies"
```

**Bound the runtime and act on the exit code:**
```bash
agy-py run "Review the staged changes" --timeout 120 || echo "agent failed/timed out ($?)"
```

**A pre-commit Git hook (`.git/hooks/pre-commit`):**
```bash
#!/usr/bin/env bash
git diff --cached | agy-py run "Review this staged diff for obvious bugs. \
Reply with only 'OK' or a bullet list of issues." --timeout 120 || exit 1
```

**GitHub Actions step (CI):**
```yaml
- name: AI review
  env:
    ANTIGRAVITY_API_KEY: ${{ secrets.ANTIGRAVITY_API_KEY }}  # stateless CI auth (see notes)
  run: |
    pip install -e .
    curl -fsSL https://antigravity.google/cli/install.sh | bash
    git diff origin/main... | agy-py run "Summarize this PR's risk" --timeout 300
```

> **Important (agy v1.0.2):** the agent's response renders only to an interactive
> terminal, so you can pipe input *in* (as above) and gate on the **exit code**,
> but you cannot capture or pipe the response *out*, and there is no JSON flag.
> `agy-py run` inherits your terminal so you see the output live. CI auth via
> `ANTIGRAVITY_API_KEY` is third-party-documented and unverified here.

## Python API

```python
from agy_py import AgyRunner, core

runner = AgyRunner()                       # locates the agy binary (raises AgyError if missing)

# prompt() inherits your terminal: agy v1.0.2 renders the response only to a TTY,
# so it prints directly and Result.stdout is empty -- only returncode is useful.
result = runner.prompt("Explain this codebase", add_dirs=["src"], timeout=120)
print("agy exit code:", result.returncode)

# Captured commands DO return output:
print(runner.version().stdout)             # e.g. "1.0.2"
print(runner.raw(["--help"]).stdout)

# Workspace trust (agy -p hangs in an untrusted folder):
if not core.is_trusted():
    core.trust_workspace()                 # add cwd to trustedWorkspaces
```

`AgyRunner` methods: `prompt(...)` (inherits the terminal), and `version()`,
`update()`, `changelog()`, `plugin(args)`, `raw(args)` (these capture output).
Each returns a `Result(returncode, stdout, stderr)` with `.ok` / `.json()`.
Module-level helpers: `get_setting()`, `set_setting()`, `settings_path()`,
`is_trusted()`, `trust_workspace()`, `trusted_workspaces()`.

## Configuration

### Files

| File | Path | Source |
|------|------|--------|
| Settings | `~/.gemini/antigravity-cli/settings.json` | official docs |
| Keybindings | `~/.gemini/antigravity-cli/keybindings.json` | official docs |
| MCP servers | `~/.gemini/config/mcp_config.json` | best-effort |
| Hooks | `~/.gemini/config/hooks.json` | best-effort |

```bash
agy-py config path                 # print the settings.json path
agy-py config get                  # dump all settings as JSON
agy-py config get editor.tabSize   # read one (dotted) key
agy-py config set verbosity low    # write a key (VALUE parsed as JSON, else string)
agy-py config set editor.tabSize 2 # nested key, numeric value
```

### Environment variables

| Variable | Purpose |
|----------|---------|
| `AGY_BINARY` | Explicit path to the `agy` executable (verified). |
| `ANTIGRAVITY_API_KEY` | Stateless auth for headless/CI (third-party-documented; unverified). |

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error — binary not found, invalid JSON, or `agy` reported failure |
| `2` | Timeout — `run --timeout` elapsed before `agy` finished |

When `agy` itself runs, `agy-py` **propagates `agy`'s own exit code**, so your
scripts see what the agent actually returned.

## Command surface & verification status

This wrapper was **verified against `agy` v1.0.2** by running `agy --help` on a
real install. Provenance, so you know what to trust:

**✅ Verified against the installed binary (`agy --help`, v1.0.2)**
- Binary name `agy`; Windows install path `%LOCALAPPDATA%\agy\bin\agy.exe`.
- Print mode `-p` (alias for `--print`: "run a single prompt non-interactively
  and print the response").
- `--sandbox`, `--dangerously-skip-permissions`, `-c`/`--continue`,
  `--conversation`, `--add-dir`.
- Subcommands `update`, `changelog`, `plugin`.

**❌ Removed — do NOT exist in `agy` v1.0.2** (they were third-party-attested):
- `--output-format json` — there is no JSON-output flag; print mode is plain text.
- `-m <model>` — no top-level model flag (model selection is config-driven).
- `inspect` subcommand.

**⚠️ Known limitations of `agy` v1.0.2 (found by testing)**
- **Workspace trust:** `agy -p` blocks on an interactive "trust this folder?"
  prompt in any workspace not listed in `trustedWorkspaces`. `agy-py run` warns
  about this; `--trust` (and `agy-py config trust`) add the folder, and
  `agy-py doctor` reports the current folder's trust state.
- **Output needs a real terminal:** print mode renders the agent's response only
  to an interactive TTY. With captured/piped/redirected stdout it emits nothing,
  so `agy-py run` **inherits your terminal** rather than capturing — you see the
  response live, but it cannot be programmatically captured or piped *out*, and
  there is no JSON output, on this version.
- **Non-interactive stdin:** without an interactive console or a real pipe
  (data + EOF), `agy -p` can block on stdin; bound scripted runs with `--timeout`.
- The MCP / hooks config paths and `ANTIGRAVITY_API_KEY` remain unverified
  (env vars don't appear in `agy --help`).

All wrapped flag names are centralized as constants in
[`agy_py/core.py`](agy_py/core.py) for easy correction on future `agy` versions.
While you confirm syntax, `agy-py raw <args>` bypasses the wrapper entirely.

## Troubleshooting & FAQ

**How do I run Google Antigravity from the command line / non-interactively?**
Use `agy-py run "your prompt"`, which invokes `agy -p` (print mode) so the agent
processes one prompt and exits — no interactive TUI.

**`agy-py run` hangs or times out (exit 2). Why?**
Two common causes on `agy` v1.0.2: (1) the folder isn't a trusted workspace, so
`agy` blocks on a now-invisible trust prompt — run `agy-py doctor` to check, then
use `--trust` or `agy-py config trust`; (2) there's no interactive terminal, so
print mode blocks on stdin and/or renders nothing. `agy-py run` is meant to be
used from a real terminal; bound scripted runs with `--timeout`.

**`agy-py` says it can't find the `agy` binary. What do I do?**
Install the binary (see [Installation](#installation)), or set
`AGY_BINARY=/full/path/to/agy`, or pass `--binary`. Run `agy-py doctor` to see
where it's looking. On Windows after install, open a **new** shell so `PATH`
refreshes (or point `AGY_BINARY` at `%LOCALAPPDATA%\agy\bin\agy.exe`).

**Can I get JSON output from the agent?**
`agy` v1.0.2 has no JSON-output flag, so `agy-py run` returns plain text. Ask the
agent to reply in JSON in your prompt, then parse the text yourself (the Python
API's `Result.json()` helps).

**Does this work on Windows, macOS, and Linux?**
Yes. Binary discovery and the default install paths are platform-aware.

**Is this an official Google project?**
No. It's an independent, unofficial wrapper around the public `agy` CLI.

**Can I use it in CI/CD or GitHub Actions?**
Yes — see [Headless usage, scripting & CI/CD](#headless-usage-scripting--cicd).
Use a non-interactive auth method since there's no browser in CI.

## agy-py vs. calling agy directly

| | Raw `agy -p` | Your own `subprocess` | **agy-py** |
|---|---|---|---|
| Non-interactive prompt | ✅ | ✅ | ✅ |
| Finds binary across OSes | ✅ (if on PATH) | ✋ you handle it | ✅ |
| Consistent exit codes (0/1/2) | partial | ✋ you map them | ✅ |
| Hard timeout (`--timeout`) | via `--print-timeout` | ✋ | ✅ |
| Importable Python API | ❌ | ✅ (reinvented) | ✅ `AgyRunner` |
| `settings.json` helpers | ❌ | ❌ | ✅ |
| Unit-testable without binary | n/a | ✋ | ✅ (mocked) |

## Development

```bash
git clone https://github.com/ddtraveller/antigravity-py
cd antigravity-py
pip install -e ".[dev]"
pytest                  # subprocess is mocked → passes without agy installed
```

Layout:

```
agy_py/
  core.py     # AgyRunner, binary discovery, settings I/O — pure stdlib, no Click
  cli.py      # Click command-line interface (thin veneer over core)
  __main__.py # python -m agy_py
tests/        # mocked-subprocess unit tests (core + CLI)
```

## Contributing

Issues and PRs are welcome — especially:

- **Verifying the not-yet-verified items** (live `agy -p` round-trip,
  `ANTIGRAVITY_API_KEY`, MCP/hooks paths) and keeping the flag constants in
  `agy_py/core.py` correct across `agy` versions.
- New thin command wrappers as the CLI surface evolves.

Please keep changes surgical, match the existing style, and add a test
(mock `subprocess` so the suite runs without the binary).

## License

[MIT](LICENSE) © the agy-py contributors.

## Related projects & references

- **Official Google Antigravity docs** — <https://antigravity.google/docs/cli-getting-started> and <https://antigravity.google/docs/cli-using>
- **Antigravity CLI launch** — <https://antigravity.google/blog/introducing-google-antigravity-cli>
- **`notebooklm-py`** (the structural template for this project) — <https://github.com/teng-lin/notebooklm-py>

---

<sub>Keywords: Google Antigravity, Antigravity 2.0, agy CLI, AGY CLI, Antigravity
command line, AI coding agent, terminal coding agent, headless AI agent, Gemini,
Python wrapper, subprocess automation, CI/CD, developer tools.</sub>
