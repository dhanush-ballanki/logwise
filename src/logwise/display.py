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

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def get_console(no_color: bool = False) -> Console:
    """Build a Console honoring `--no-color` / `LOGWISE_NO_COLOR` / `NO_COLOR`."""
    return Console(
        no_color=no_color or bool(os.getenv("LOGWISE_NO_COLOR")),
    )


def use_rich(console: Console) -> bool:
    """Rich only when attached to a real terminal with color enabled."""
    return bool(console.is_terminal) and not console.no_color


def error_header(console: Console, exit_code: int, plain: bool) -> None:
    """`Error occurred (exit code: N)` — loud in rich, legacy text in plain."""
    if plain:
        typer.echo(f"Error occurred (exit code: {exit_code})")
    else:
        console.print(
            f"[bold red]:x: Error occurred[/] [red](exit code: {exit_code})[/]"
        )


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


def analysis(console: Console, summary: str, issues: list,
             ai_analysis: dict | None, plain: bool, *,
             show_summary: bool = True,
             ai_label: str = "AI Enhanced Analysis:") -> None:
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
        console.print(
            Panel(
                Markdown(f"{ai_analysis['reason']}\n\n{ai_analysis['fixes']}"),
                title="[bold magenta]:sparkles: AI analysis[/]",
                subtitle=f"[dim]{provider} / {model}[/]",
                border_style="magenta",
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
