# agy-py — Python wrapper for the Google Antigravity `agy` CLI

> **Drive Google Antigravity 2.0's `agy` terminal coding agent from Python and the shell** — headless prompts, JSON output, scripting, and CI/CD automation, with a clean `subprocess`-based core and a Click command-line interface.

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)
![Google Antigravity: unofficial wrapper](https://img.shields.io/badge/Google%20Antigravity-unofficial%20wrapper-lightgrey.svg)
![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

`agy-py` is a small, dependency-light **Python wrapper around the Google
Antigravity CLI** (the `agy` binary introduced with **Antigravity 2.0** at
Google I/O 2026). It lets you run Antigravity's AI coding agent
**non-interactively** — one-shot prompts, structured JSON results, stdin
pipelines, and predictable exit codes — so you can call the agent from Python
programs, shell scripts, Git hooks, and CI/CD pipelines instead of the
interactive terminal UI.

It does **not** reimplement the agent. It wraps the official `agy` binary and
gives you a tidy, testable surface — modeled on the structure of
[`notebooklm-py`](https://github.com/teng-lin/notebooklm-py): a pure-stdlib core
plus a thin CLI, `--json` everywhere it helps, and a stable `0 / 1 / 2` exit-code
contract.

> **Unofficial.** This project is not affiliated with, endorsed by, or supported
> by Google. "Antigravity", "Google Antigravity", and "Gemini" are trademarks of
> Google LLC. See [Command surface & verification status](#command-surface--verification-status)
> for exactly which behaviors are confirmed by official docs vs. best-effort.

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

- **Headless by default** — wraps `agy -p "<prompt>"` (command mode) so a single
  prompt runs and exits, perfect for scripts.
- **Structured output** — `--json` adds `--output-format json` and pretty-prints
  the parsed result, ready for `jq` or `json.loads`.
- **Robust binary discovery** — finds `agy` on `PATH`, via `$AGY_BINARY`, or at
  the platform's default install path; one clear error if it can't.
- **Predictable failures** — every error is a clean stderr message plus a
  documented exit code (no stack traces in your pipeline).
- **Importable** — `from agy_py import AgyRunner` to call the agent from Python.
- **Tested without the binary** — the core mocks `subprocess`, so `pytest` is
  green even on machines where `agy` isn't installed.

## Features

| Capability | How |
|------------|-----|
| Run one-shot prompts (headless) | `agy-py run "..."` → `agy -p "..."` |
| JSON output for parsing | `agy-py run "..." --json` |
| Pick a model | `agy-py run "..." -m <model>` |
| Sandbox / skip-permission overrides | `--sandbox`, `--skip-permissions` |
| Pipe data into the agent | `cat file | agy-py run "..."` (stdin forwarded) |
| Timeout long runs | `--timeout SECONDS` (exit code 2) |
| Check install & config health | `agy-py doctor` |
| Read/write `settings.json` | `agy-py config get/set/path` |
| Inspect loaded rules/skills/hooks/MCP | `agy-py inspect` |
| Update / version | `agy-py update`, `agy-py version` |
| Raw escape hatch | `agy-py raw <anything>` |
| Use as a Python library | `from agy_py import AgyRunner` |

## Requirements

- **Python 3.9+**
- The **`agy` binary** (Google Antigravity 2.0 CLI) — see below.
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
# Windows (PowerShell) → installs to %LOCALAPPDATA%\Antigravity\agy.exe
irm https://antigravity.google/cli/install.ps1 | iex
```
```bash
# macOS / Linux → installs to ~/.local/bin/agy
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

On first run, `agy` authenticates via your OS keyring or a browser Google
Sign-In. Verify everything is wired up:

```bash
agy-py doctor
```

### Binary discovery order

`agy-py` locates the executable in this order:

1. `--binary /path/to/agy`
2. `$AGY_BINARY` environment variable
3. `agy` on your `PATH`
4. Platform default: `%LOCALAPPDATA%\Antigravity\agy.exe` (Windows) or
   `~/.local/bin/agy` (macOS/Linux)

If none resolve, every command fails fast with an actionable message (exit 1).

## Quickstart

```bash
agy-py doctor                          # Is agy installed? Where's its config?
agy-py version                         # agy --version
agy-py run "Write a Python hello world"
agy-py run "Summarize the repo" --json # parsed + pretty-printed JSON
cat error.log | agy-py run "Explain the root cause of this stack trace"
```

## Command reference

| Command | Wraps / does | Key options |
|---------|--------------|-------------|
| `agy-py run "PROMPT"` | `agy -p "PROMPT"` (headless command mode) | `--json`, `-m/--model`, `--sandbox`, `--skip-permissions`, `--timeout`, `--binary` |
| `agy-py version` | `agy --version` | `--binary` |
| `agy-py update` | `agy update` | `--binary` |
| `agy-py inspect` | `agy inspect` (rules, skills, hooks, MCP) | `--binary` |
| `agy-py raw ARGS…` | passes `ARGS` straight to `agy` | (uses `$AGY_BINARY`/`PATH`) |
| `agy-py doctor` | checks binary + config locations | `--json`, `--binary` |
| `agy-py auth info\|login\|logout` | describes the keyring/browser auth model | — |
| `agy-py config path` | prints `settings.json` location | — |
| `agy-py config get [KEY]` | reads all settings or a dotted `KEY` | `--json` |
| `agy-py config set KEY VALUE` | writes a dotted `KEY` (`VALUE` parsed as JSON) | — |
| `agy-py config mcp-path` / `hooks-path` | prints MCP / hooks config paths (best-effort) | — |

Run `agy-py --help` or `agy-py <command> --help` for full details.

## Headless usage, scripting & CI/CD

`agy-py run` is built for non-interactive use. Stdin is **forwarded** to `agy`,
so shell pipelines work as expected.

**Pipe a file in as context:**
```bash
cat sales.csv | agy-py run "Summarize this data and flag anomalies"
```

**Parse JSON output with `jq`:**
```bash
agy-py run "List the API endpoints in routes.js" --json | jq '.endpoints[]'
```

**Use it from Python in a larger program** — see [Python API](#python-api).

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
    ANTIGRAVITY_API_KEY: ${{ secrets.ANTIGRAVITY_API_KEY }}  # stateless auth for CI
  run: |
    pip install -e .
    irm https://antigravity.google/cli/install.sh | bash   # or cache the binary
    git diff origin/main... | agy-py run "Summarize this PR's risk" --json
```

> CI authentication via `ANTIGRAVITY_API_KEY` is documented by third-party guides
> (see [verification status](#command-surface--verification-status)); confirm the
> exact variable name against your `agy` version.

## Python API

```python
from agy_py import AgyRunner, AgyError

runner = AgyRunner()                      # locates the agy binary (raises AgyError if missing)

result = runner.prompt("Explain this codebase", json_output=True, timeout=120)
print("exit:", result.returncode)
data = result.json()                      # parsed JSON (raises AgyError on bad output)

# Pass arbitrary args through:
print(runner.raw(["--help"]).stdout)

try:
    AgyRunner("/nonexistent/agy")
except AgyError as e:
    print(e, "→ exit code", e.exit_code)
```

`AgyRunner` methods: `prompt(...)`, `version()`, `update()`, `inspect()`,
`raw(args)`. Each returns a `Result(returncode, stdout, stderr)` with `.ok` and
`.json()` helpers. Settings helpers live at module level:
`get_setting()`, `set_setting()`, `settings_path()`.

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
| `AGY_BINARY` | Explicit path to the `agy` executable. |
| `ANTIGRAVITY_API_KEY` | Stateless auth for headless/CI use (best-effort; verify name). |

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error — binary not found, invalid JSON, or `agy` reported failure |
| `2` | Timeout — `run --timeout` elapsed before `agy` finished |

When `agy` itself runs, `agy-py` **propagates `agy`'s own exit code**, so your
scripts see what the agent actually returned.

## Command surface & verification status

Antigravity 2.0 is brand new (announced May 2026). This wrapper was built from
the **official `antigravity.google` docs** *and* third-party hands-on guides.
Here's exactly what to trust — and what to double-check against your installed
binary.

**✅ Confirmed by official `antigravity.google` documentation**
- Binary name `agy`; the install commands and install paths.
- The authentication model (OS keyring → browser sign-in; SSH paste-back code;
  enterprise via GCP project).
- Config at `~/.gemini/antigravity-cli/settings.json` (and `keybindings.json`).
- Launch overrides `--sandbox` and `--dangerously-skip-permissions`.

**⚠️ Third-party tutorials only (NOT yet in official docs — best-effort)**
- The headless `agy -p "<prompt>"` command mode.
- `--output-format json`.
- `-m <model>`.
- `ANTIGRAVITY_API_KEY` and the MCP / hooks config paths.

All wrapped flag names are centralized as constants in
[`agy_py/core.py`](agy_py/core.py). If your `agy` build disagrees, **fix them in
one place**. While you confirm syntax, `agy-py raw <args>` bypasses the wrapper
entirely (e.g. `agy-py raw --help`). Contributions that verify these against a
real binary are very welcome — see [Contributing](#contributing).

## Troubleshooting & FAQ

**How do I run Google Antigravity from the command line / headlessly?**
Use `agy-py run "your prompt"`, which invokes `agy -p` (command mode) so the
agent processes one prompt and exits — no interactive TUI.

**How do I get JSON output from the Antigravity agent?**
Add `--json`: `agy-py run "..." --json`. It appends `--output-format json` and
pretty-prints the parsed result; pipe it to `jq` or read it with `json.loads`.

**`agy-py` says it can't find the `agy` binary. What do I do?**
Install the binary (see [Installation](#installation)), or set
`AGY_BINARY=/full/path/to/agy`, or pass `--binary`. Run `agy-py doctor` to see
where it's looking. On Windows after install, open a **new** shell so `PATH`
refreshes (or point `AGY_BINARY` at `%LOCALAPPDATA%\Antigravity\agy.exe`).

**Does this work on Windows, macOS, and Linux?**
Yes. Binary discovery and the default install paths are platform-aware.

**Is this an official Google project?**
No. It's an independent, unofficial wrapper around the public `agy` CLI.

**What's the difference between `agy` and the old `gemini` CLI?**
`agy` is the Antigravity 2.0 CLI; the `gemini` CLI is the earlier, separate tool.
This wrapper targets `agy` only. (Antigravity ships an `agy migrate` command to
import legacy Gemini CLI state.)

**Can I use it in CI/CD or GitHub Actions?**
Yes — see [Headless usage, scripting & CI/CD](#headless-usage-scripting--cicd).
Use a non-interactive auth method (`ANTIGRAVITY_API_KEY`) since there's no
browser in CI.

**Does it support MCP servers and hooks?**
`agy-py inspect` reports loaded MCP servers/hooks, and `config mcp-path` /
`config hooks-path` locate the config files (paths are best-effort). Editing
those files is currently manual.

## agy-py vs. calling agy directly

| | Raw `agy -p` | Your own `subprocess` | **agy-py** |
|---|---|---|---|
| Headless prompt | ✅ | ✅ | ✅ |
| Finds binary across OSes | ✅ (if on PATH) | ✋ you handle it | ✅ |
| JSON parse + pretty-print | ✋ manual | ✋ manual | ✅ `--json` |
| Consistent exit codes | partial | ✋ you map them | ✅ `0/1/2` |
| Importable Python API | ❌ | ✅ (reinvented) | ✅ `AgyRunner` |
| `settings.json` helpers | ❌ | ❌ | ✅ |
| Unit-testable without binary | n/a | ✋ | ✅ (mocked) |

## Development

```bash
git clone <your-fork-url> antigravity-py
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

- **Verifying the best-effort flags** (`-p`, `--output-format json`, `-m`,
  `ANTIGRAVITY_API_KEY`, MCP/hooks paths) against a live `agy` install and
  correcting the constants in `agy_py/core.py`.
- New thin command wrappers as the official CLI surface stabilizes.

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
command line, AI coding agent, terminal coding agent, headless AI, Gemini,
Python wrapper, subprocess, automation, CI/CD, developer tools.</sub>
