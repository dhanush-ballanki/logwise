"""Terminal rendering for LogWise (the only module that knows about color).

All failure/analysis output goes through here so `run` and `analyze`
never drift apart. Two modes:

- Rich (terminal): red error header, stderr panel, colored issue rows,
  Markdown AI panel, table-backed `list`.
- Plain (piped/redirected, `NO_COLOR`/`LOGWISE_NO_COLOR`, or `--no-color`):
  the exact legacy `print()` text, byte-for-byte, so scripts keep working.

Success-path stdout never touches this module — it stays a plain print.
"""

import os
import sys
from contextlib import nullcontext

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

#: Accent color per AI provider (AI panel, spinner). Unknown → magenta.
PROVIDER_THEMES = {
    "gemini": "blue",
    "openai": "green",
    "deepseek": "violet",
    "groq": "orange1",
    "openrouter": "cyan",
    "ollama": "grey62",
}


def provider_color(name: str | None) -> str:
    """Accent color for a provider name (case-insensitive)."""
    return PROVIDER_THEMES.get((name or "").strip().lower(), "magenta")


def get_console(no_color: bool = False) -> Console:
    """Build a Console honoring `--no-color` / `LOGWISE_NO_COLOR` / `NO_COLOR`."""
    return Console(
        no_color=no_color or bool(os.getenv("LOGWISE_NO_COLOR")),
    )


def use_rich(console: Console) -> bool:
    """Rich only when attached to a real terminal with color enabled."""
    return bool(console.is_terminal) and not console.no_color


def interactive(console: Console) -> bool:
    """True when safe to prompt: terminal output AND tty stdin."""
    try:
        stdin_tty = sys.stdin.isatty()
    except Exception:
        stdin_tty = False
    return bool(console.is_terminal) and stdin_tty


def ai_progress(console: Console, provider: str | None, model: str | None, plain: bool):
    """Spinner shown while waiting on an AI provider (no-op when plain).

    Usage: `with ai_progress(console, provider, model, plain): ...`
    """
    if plain:
        return nullcontext()
    accent = provider_color(provider)
    label = escape(f"{provider or 'ai'} / {model or '?'}")
    return console.status(f"[{accent}]Consulting {label}…[/]", spinner="dots")


def prompt_retry(console: Console) -> bool:
    """Ask whether to re-run the failed command (False when non-interactive)."""
    if not interactive(console):
        return False
    try:
        return typer.confirm("Retry command?", default=False)
    except Exception:
        return False


def prompt_ai(console: Console) -> bool:
    """Offer AI analysis after a non-AI failure (False when non-interactive)."""
    if not interactive(console):
        return False
    try:
        return typer.confirm("Analyze with AI?", default=False)
    except Exception:
        return False


def prompt_rerun(console: Console) -> bool:
    """Offer to re-run a logged command from `analyze`."""
    if not interactive(console):
        return False
    try:
        return typer.confirm("Re-run the logged command?", default=False)
    except Exception:
        return False


def prompt_edit_command(console: Console, current: str) -> str | None:
    """Let the user edit a command before re-running it.

    Returns the (possibly unchanged) command, or None if the user aborts
    or prompts are unavailable. Enter keeps `current` (typer default).
    """
    if not interactive(console):
        return None
    try:
        return typer.prompt("Edit command", default=current)
    except KeyboardInterrupt:
        return None
    except Exception:
        return None


def error_header(console: Console, exit_code: int, plain: bool) -> None:
    """`Error occurred (exit code: N)` — loud in rich, legacy text in plain."""
    if plain:
        typer.echo(f"Error occurred (exit code: {exit_code})")
    else:
        console.print(f"[bold red]:x: Error occurred[/] [red](exit code: {exit_code})[/]")


def stderr_block(console: Console, stderr: str, plain: bool) -> None:
    """Captured stderr — red panel in rich, labeled text in plain."""
    if plain:
        typer.echo("Stderr captured:")
        typer.echo(stderr)
    else:
        console.print(
            Panel(
                Text(stderr or "(empty)", overflow="fold"),
                title="[red]stderr[/]",
                border_style="red",
            )
        )


def analysis(
    console: Console,
    summary: str,
    issues: list,
    ai_analysis: dict | None,
    plain: bool,
    *,
    show_summary: bool = True,
    ai_label: str = "AI Enhanced Analysis:",
) -> None:
    """Summary line + rule issues + optional AI panel.

    `show_summary=False` skips the summary (for callers that already
    printed it, e.g. `analyze` under its "Log Summary:" label). `ai_label`
    keeps each command's legacy plain-text header byte-identical.
    """
    if plain:
        if show_summary:
            typer.echo("\nAnalysis:")
            typer.echo(summary)
        for issue in issues:
            typer.echo(f"- Reason: {issue['description']} ({issue['root_cause']})")
            typer.echo(f"  Steps to fix: {issue['fixes']}")
        if ai_analysis:
            typer.echo(f"\n{ai_label}")
            typer.echo(f"Reason: {ai_analysis['reason']}")
            typer.echo(f"Steps to fix: {ai_analysis['fixes']}")
        return

    console.print(f"[bold]{escape(summary)}[/]")
    for n, issue in enumerate(issues, 1):
        console.print(
            f"[yellow]:warning: {n}. {escape(issue['description'])}[/]"
            f" [dim]({escape(issue['root_cause'])})[/]"
            f" [dim][{escape(str(issue.get('rule_id', '?')))}][/]"
        )
        console.print(f"   [green]->[/] {escape(issue['fixes'])}")
    if ai_analysis:
        provider = escape(str(ai_analysis.get("provider", "?")))
        model = escape(str(ai_analysis.get("model", "?")))
        accent = provider_color(ai_analysis.get("provider"))
        console.print(
            Panel(
                Markdown(f"{ai_analysis['reason']}\n\n{ai_analysis['fixes']}"),
                title=f"[bold {accent}]:sparkles: AI analysis[/]",
                subtitle=f"[dim]{provider} / {model}[/]",
                border_style=accent,
            )
        )


def log_table(console: Console, entries: list, plain: bool) -> None:
    """Saved-logs listing — table in rich, one-per-line in plain.

    `entries` is a list of {"file", "command", "exit_code"} dicts; any of
    the latter two may be None for unreadable files.
    """
    if plain:
        if not entries:
            typer.echo("No logs found.")
        for entry in entries:
            typer.echo(entry["file"])
        return

    if not entries:
        console.print("[dim]No logs found.[/]")
        return
    table = Table(title="Captured logs")
    table.add_column("File", style="cyan")
    table.add_column("Command", overflow="fold")
    table.add_column("Exit", justify="right", style="red")
    for entry in entries:
        table.add_row(
            escape(entry["file"]),
            escape(entry.get("command")) if entry.get("command") else "[dim](unreadable)[/]",
            str(entry["exit_code"]) if entry.get("exit_code") is not None else "?",
        )
    console.print(table)
