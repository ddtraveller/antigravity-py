"""Click command-line interface for agy-py.

A thin veneer over :mod:`agy_py.core`. Commands print ``agy``'s stdout/stderr
and propagate its exit code; wrapper-level failures exit with the codes defined
in :mod:`agy_py.core` (1 = error, 2 = timeout).
"""

from __future__ import annotations

import functools
import json
import sys

import click

from . import __version__, core
from .core import AgyError, AgyRunner

_BINARY_OPTION = click.option(
    "--binary",
    envvar=core.BINARY_ENV_VAR,
    default=None,
    help="Path to the agy binary (defaults to $AGY_BINARY / PATH / install dir).",
)


def handle_errors(func):
    """Turn :class:`AgyError` into a clean stderr message + exit code."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AgyError as exc:
            click.echo(str(exc), err=True)
            sys.exit(exc.exit_code)

    return wrapper


def _emit_and_exit(result: core.Result) -> None:
    if result.stdout:
        click.echo(result.stdout, nl=False)
    if result.stderr:
        click.echo(result.stderr, err=True, nl=False)
    sys.exit(result.returncode)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="agy-py")
def cli() -> None:
    """Python wrapper around Google Antigravity's `agy` CLI."""


@cli.command()
@click.argument("prompt")
@click.option("--json", "json_output", is_flag=True,
              help="Add `--output-format json` and pretty-print the parsed result.")
@click.option("-m", "--model", default=None, help="Model id (agy -m).")
@click.option("--sandbox", is_flag=True, help="Force sandboxed execution (agy --sandbox).")
@click.option("--skip-permissions", is_flag=True,
              help="agy --dangerously-skip-permissions (bypass safety prompts).")
@click.option("--timeout", type=float, default=None,
              help="Kill agy after N seconds (exits 2 on timeout).")
@_BINARY_OPTION
@handle_errors
def run(prompt, json_output, model, sandbox, skip_permissions, timeout, binary):
    """Run a one-shot PROMPT through `agy -p` (headless command mode).

    Piped stdin is forwarded to agy, so you can do:

        cat data.csv | agy-py run "Summarize this data"
    """
    runner = AgyRunner(binary)
    result = runner.prompt(
        prompt,
        json_output=json_output,
        model=model,
        sandbox=sandbox,
        skip_permissions=skip_permissions,
        timeout=timeout,
    )
    if json_output and result.stdout.strip():
        click.echo(json.dumps(result.json(), indent=2))
        if result.stderr:
            click.echo(result.stderr, err=True, nl=False)
        sys.exit(result.returncode)
    _emit_and_exit(result)


@cli.command()
@_BINARY_OPTION
@handle_errors
def version(binary):
    """Show the installed agy binary version (agy --version)."""
    _emit_and_exit(AgyRunner(binary).version())


@cli.command()
@_BINARY_OPTION
@handle_errors
def update(binary):
    """Update the agy binary to the latest release (agy update)."""
    _emit_and_exit(AgyRunner(binary).update())


@cli.command()
@_BINARY_OPTION
@handle_errors
def inspect(binary):
    """Show loaded rules, skills, hooks and MCP servers (agy inspect)."""
    _emit_and_exit(AgyRunner(binary).inspect())


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@handle_errors
def raw(args):
    """Pass ARGS straight through to the agy binary (escape hatch).

    Uses $AGY_BINARY / PATH to locate agy. Example: agy-py raw --help
    """
    _emit_and_exit(AgyRunner(None).raw(list(args)))


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Emit diagnostics as JSON.")
@_BINARY_OPTION
@handle_errors
def doctor(json_output, binary):
    """Check that agy is installed and locate its config files."""
    info = core.diagnostics(binary)
    if json_output:
        click.echo(json.dumps(info, indent=2))
    else:
        if info["binary_found"]:
            click.echo(f"agy binary : OK  {info['binary']}")
        else:
            click.echo("agy binary : NOT FOUND")
            click.echo(f"             {info.get('binary_error', '')}")
        click.echo(f"settings   : {info['settings_path']} "
                   f"({'exists' if info['settings_exists'] else 'missing'})")
        click.echo(f"agent data : {info['gemini_dir']} "
                   f"({'exists' if info['gemini_dir_exists'] else 'missing'})")
    sys.exit(core.EXIT_OK if info["binary_found"] else core.EXIT_ERROR)


# --- auth helpers (interactive auth can't be driven headlessly) ------------

@cli.group()
def auth() -> None:
    """Authentication helpers (agy auth is keyring/browser based)."""


@auth.command("info")
@handle_errors
def auth_info():
    """Describe the agy auth model and check for local agent data."""
    click.echo("agy authentication (per official docs):")
    click.echo("  1. Silent lookup in the OS secure keyring.")
    click.echo("  2. Fallback to browser Google Sign-In on first run.")
    click.echo("  3. SSH/remote: agy prints a URL + paste-back code.")
    click.echo("  4. Enterprise: connect your GCP project during onboarding.")
    data_dir = core.Path.home() / ".gemini" / "antigravity"
    click.echo(f"\nlocal agent data: {data_dir} "
               f"({'present' if data_dir.exists() else 'absent'})")


@auth.command("login")
@handle_errors
def auth_login():
    """How to authenticate (must be done interactively)."""
    click.echo("Run `agy` once with no arguments; it opens your browser for "
               "Google Sign-In. For CI, set ANTIGRAVITY_API_KEY instead.")


@auth.command("logout")
@handle_errors
def auth_logout():
    """How to clear credentials."""
    click.echo("Type `/logout` inside the agy TUI to clear saved credentials.")


# --- config (settings.json read/write; MCP & hooks path helpers) -----------

@cli.group()
def config() -> None:
    """Read/write agy settings.json and locate MCP / hooks config."""


@config.command("path")
@handle_errors
def config_path():
    """Print the settings.json path."""
    click.echo(str(core.settings_path()))


@config.command("get")
@click.argument("key", required=False)
@click.option("--json", "json_output", is_flag=True, help="Emit value as JSON.")
@handle_errors
def config_get(key, json_output):
    """Print all settings, or the value at dotted KEY (e.g. editor.tabSize)."""
    value = core.get_setting(key)
    if json_output or not isinstance(value, str):
        click.echo(json.dumps(value, indent=2))
    else:
        click.echo(value)


@config.command("set")
@click.argument("key")
@click.argument("value")
@handle_errors
def config_set(key, value):
    """Set dotted KEY to VALUE (parsed as JSON, else treated as a string)."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value
    core.set_setting(key, parsed)
    click.echo(f"Set {key} = {json.dumps(parsed)}")


@config.command("mcp-path")
@handle_errors
def config_mcp_path():
    """Print the MCP config path (best-effort; verify against your install)."""
    click.echo(str(core.mcp_config_path()))


@config.command("hooks-path")
@handle_errors
def config_hooks_path():
    """Print the hooks config path (best-effort; verify against your install)."""
    click.echo(str(core.hooks_path()))


if __name__ == "__main__":
    cli()
