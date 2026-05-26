# agy-py

A thin Python wrapper around Google **Antigravity's `agy` CLI** (Antigravity
2.0, announced at I/O 2026). It shells out to the `agy` binary, parses its
output, and exposes a small, scriptable command set — modeled on the structure
of [`notebooklm-py`](https://github.com/teng-lin/notebooklm-py) (stdlib core +
Click CLI + `--json` output + consistent exit codes).

It does **not** reimplement the agent. It wraps the binary so you can drive
`agy`'s headless command mode from Python and scripts.

## Install

```bash
# from the repo root
pip install -e .
# with test deps
pip install -e ".[dev]"
```

You also need the real `agy` binary:

```powershell
# Windows  -> installs to %LOCALAPPDATA%\Antigravity\agy.exe
irm https://antigravity.google/cli/install.ps1 | iex
```
```bash
# macOS / Linux -> installs to ~/.local/bin/agy
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

`agy-py` finds the binary via, in order: `--binary`, `$AGY_BINARY`, `PATH`,
then the platform default install path above.

## Usage

```bash
agy-py doctor                       # is agy installed? where's the config?
agy-py version                      # agy --version
agy-py run "Write a hello world"    # agy -p "..."  (headless command mode)
agy-py run "Summarize" --json       # adds --output-format json, pretty-prints
agy-py run "Sort it" -m gpt-oss-120b --sandbox
cat data.csv | agy-py run "Summarize this data"   # stdin is forwarded to agy
agy-py update                       # agy update
agy-py inspect                      # loaded rules/skills/hooks/MCP servers
agy-py raw --help                   # pass anything straight through to agy

agy-py config path                  # ~/.gemini/antigravity-cli/settings.json
agy-py config get editor.tabSize
agy-py config set verbosity low

agy-py auth info                    # describe the auth model + check local data
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | success |
| 1 | error (binary not found, bad JSON, agy failure) |
| 2 | timeout (`run --timeout`) |

When `agy` runs successfully, `agy-py` propagates **agy's own exit code**.

### Python API

```python
from agy_py import AgyRunner

runner = AgyRunner()                       # locates the agy binary
result = runner.prompt("Explain X", json_output=True)
print(result.returncode, result.json())
```

## ⚠️ Verification status of the wrapped surface

This wrapper was built against the official docs **and** third-party hands-on
guides (Antigravity 2.0 is brand new). Provenance, so you know what to trust:

**Confirmed by official `antigravity.google` docs:**
- Binary name `agy`, the install commands and paths.
- Auth model (OS keyring → browser sign-in; SSH paste-back; enterprise GCP).
- Config at `~/.gemini/antigravity-cli/settings.json` (+ `keybindings.json`).
- Launch overrides `--sandbox` and `--dangerously-skip-permissions`.

**Third-party tutorials only (NOT in official docs — treat as best-effort):**
- The headless `agy -p "<prompt>"` command mode.
- `--output-format json`.
- `-m <model>`.
- The MCP / hooks config file paths (`config mcp-path`, `config hooks-path`).

All of these flag names are centralized as constants in
[`agy_py/core.py`](agy_py/core.py); if the installed binary disagrees, fix them
in one place. `agy-py raw ...` lets you bypass the wrapper entirely while you
confirm syntax (e.g. `agy-py raw --help`).

## Develop

```bash
pip install -e ".[dev]"
pytest        # mocks subprocess; passes without agy installed
```
