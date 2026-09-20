import json
import os
import sys
from contextlib import nullcontext

import typer

from . import display
from .analyze import analyze_log, list_logs, prune_logs
from .capture import capture_and_run
from .env import load_dotenv
from .paths import ensure_log_dir, get_log_dir
from .providers import PROVIDERS

load_dotenv()  # .env / LOGWISE_ENV_FILE, before any resolve_*() runs
ensure_log_dir()  # logs/ exists before any command runs


def _ensure_utf8_output() -> None:
    """Use UTF-8 for CLI output so model text never crashes Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_ensure_utf8_output()

app = typer.Typer(help="LogWise: Intelligent Log Analyzer")

_PROVIDER_HELP = f"AI provider ({', '.join(sorted(PROVIDERS))}). Env: LOGWISE_PROVIDER."
_NO_COLOR_HELP = "Disable colored output. Env: LOGWISE_NO_COLOR."
_NO_PROMPT_HELP = "Never prompt (retry / edit / AI offer / rerun). Env: LOGWISE_NO_PROMPT."


def _prompts_enabled(no_prompt: bool) -> bool:
    return not no_prompt and not os.getenv("LOGWISE_NO_PROMPT")


@app.command()
def run(
    command: str,
    ai: bool = typer.Option(False, "--ai", help="Use AI enhanced analysis on errors"),
    provider: str = typer.Option(None, "--provider", help=_PROVIDER_HELP),
    model: str = typer.Option(None, "--model", help="Model override. Env: LOGWISE_MODEL."),
    no_color: bool = typer.Option(False, "--no-color", help=_NO_COLOR_HELP),
    no_prompt: bool = typer.Option(False, "--no-prompt", help=_NO_PROMPT_HELP),
):
    """Run a command: Output normally on success, analyze errors with reasons/fixes"""
    console = display.get_console(no_color=no_color)
    log_name = capture_and_run(
        command, use_ai=ai, provider=provider, model=model, no_color=no_color
    )
    if log_name is None or not _prompts_enabled(no_prompt):
        return
    current = command
    while display.prompt_retry(console):
        edited = display.prompt_edit_command(console, current)
        if edited is None:
            break
        current = edited
        log_name = capture_and_run(
            current, use_ai=ai, provider=provider, model=model, no_color=no_color
        )
        if log_name is None:
            return
    if not ai and display.prompt_ai(console):
        plain = not display.use_rich(console)
        with display.ai_progress(console, provider, model, plain):
            result = analyze_log(log_name, use_ai=True, provider=provider, model=model)
        display.analysis(
            console,
            result.get("summary", ""),
            result.get("issues", []),
            result.get("ai_analysis"),
            plain,
            show_summary=not plain,
            ai_label="AI Analysis:",
        )


@app.command()
def analyze(
    log_file: str = typer.Argument(..., help="Log file to analyze"),
    ai: bool = typer.Option(False, "--ai", help="Use AI for enchanced analysis"),
    provider: str = typer.Option(None, "--provider", help=_PROVIDER_HELP),
    model: str = typer.Option(None, "--model", help="Model override. Env: LOGWISE_MODEL."),
    no_color: bool = typer.Option(False, "--no-color", help=_NO_COLOR_HELP),
    no_prompt: bool = typer.Option(False, "--no-prompt", help=_NO_PROMPT_HELP),
):
    """
    Analyze a captured log for errors
    """
    console = display.get_console(no_color=no_color)
    plain = not display.use_rich(console)
    if ai:
        context = display.ai_progress(console, provider, model, plain)
    else:
        context = nullcontext()
    with context:
        result = analyze_log(log_file, use_ai=ai, provider=provider, model=model)
    if "error" in result:
        typer.echo(result["error"])
        return

    if not plain:
        console.print("[bold]Log Summary:[/]")
    else:
        typer.echo("Log Summary:")
        typer.echo(result["summary"])
    display.analysis(
        console,
        result["summary"],
        result.get("issues", []),
        result.get("ai_analysis"),
        plain,
        show_summary=not plain,
        ai_label="AI Analysis:",
    )
    if (
        _prompts_enabled(no_prompt)
        and result.get("log")
        and result["log"].get("command")
        and display.prompt_rerun(console)
    ):
        edited = display.prompt_edit_command(console, result["log"]["command"])
        if edited is not None:
            capture_and_run(
                edited,
                use_ai=ai,
                provider=provider,
                model=model,
                no_color=no_color,
            )


@app.command()
def list(
    no_color: bool = typer.Option(False, "--no-color", help=_NO_COLOR_HELP),
):
    """
    List all captured logs.
    """
    log_dir = get_log_dir()
    entries = []
    for name in list_logs():
        entry = {"file": name, "command": None, "exit_code": None}
        try:
            with open(os.path.join(log_dir, name)) as f:
                log = json.load(f)
            entry["command"] = log.get("command")
            entry["exit_code"] = log.get("exit_code")
        except (OSError, ValueError):
            pass
        entries.append(entry)
    console = display.get_console(no_color=no_color)
    display.log_table(console, entries, not display.use_rich(console))


@app.command()
def prune(
    keep: int = typer.Option(50, "--keep", help="Keep the newest N eligible logs."),
    older_than: float = typer.Option(
        None, "--older-than", help="Only delete logs older than N days."
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Delete without asking."),
    no_color: bool = typer.Option(False, "--no-color", help=_NO_COLOR_HELP),
):
    """
    Delete old logs (by count and/or age). Asks first unless --yes.
    """
    preview = prune_logs(keep=keep, older_than_days=older_than, dry_run=True)
    doomed = preview["doomed"]
    console = display.get_console(no_color=no_color)
    plain = not display.use_rich(console)
    if not doomed:
        if plain:
            typer.echo("Nothing to prune.")
        else:
            console.print("[dim]Nothing to prune.[/]")
        return
    if plain:
        typer.echo(f"Would delete {len(doomed)} log(s):")
        for name in doomed:
            typer.echo(f"  {name}")
    else:
        console.print(f"[bold]Would delete {len(doomed)} log(s):[/]")
        for name in doomed:
            console.print(f"  [cyan]{name}[/]")
    if not yes:
        try:
            confirmed = display.interactive(console) and typer.confirm(
                "Delete these logs?", default=False
            )
        except Exception:
            confirmed = False
        if not confirmed:
            typer.echo("Aborted.")
            return
    result = prune_logs(keep=keep, older_than_days=older_than)
    typer.echo(f"Deleted {len(result['deleted'])} log(s), {result['kept']} kept.")


if __name__ == "__main__":
    app()
