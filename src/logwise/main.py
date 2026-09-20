import json
import os
import sys
import typer
from .env import load_dotenv
from . import display
from .capture import capture_and_run
from .analyze import analyze_log,list_logs
from .paths import get_log_dir
from .providers import PROVIDERS

load_dotenv()  # .env / LOGWISE_ENV_FILE, before any resolve_*() runs


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

@app.command()
def run(
    command: str,
    ai: bool = typer.Option(False, "--ai", help="Use AI enhanced analysis on errors"),
    provider: str = typer.Option(None, "--provider", help=_PROVIDER_HELP),
    model: str = typer.Option(None, "--model", help="Model override. Env: LOGWISE_MODEL."),
    no_color: bool = typer.Option(False, "--no-color", help=_NO_COLOR_HELP),
):
    """ Run a command: Output normally on success, analyze errors with reasons/fixes """
    capture_and_run(command, use_ai=ai, provider=provider, model=model,
                    no_color=no_color)

@app.command()
def analyze(
    log_file: str = typer.Argument(..., help="Log file to analyze"),
    ai: bool = typer.Option( False, "--ai", help="Use AI for enchanced analysis"),
    provider: str = typer.Option(None, "--provider", help=_PROVIDER_HELP),
    model: str = typer.Option(None, "--model", help="Model override. Env: LOGWISE_MODEL."),
    no_color: bool = typer.Option(False, "--no-color", help=_NO_COLOR_HELP),
):
    """
        Analyze a captured log for errors
    """
    result = analyze_log(log_file,use_ai=ai,provider=provider,model=model)
    if 'error' in result:
        typer.echo(result['error'])
        return

    console = display.get_console(no_color=no_color)
    plain = not display.use_rich(console)
    if not plain:
        console.print("[bold]Log Summary:[/]")
    else:
        typer.echo("Log Summary:")
        typer.echo(result['summary'])
    display.analysis(console, result['summary'],
                     result.get('issues', []),
                     result.get('ai_analysis'), plain,
                     show_summary=not plain, ai_label="AI Analysis:")

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
            with open(os.path.join(log_dir, name), 'r') as f:
                log = json.load(f)
            entry["command"] = log.get("command")
            entry["exit_code"] = log.get("exit_code")
        except (OSError, ValueError):
            pass
        entries.append(entry)
    console = display.get_console(no_color=no_color)
    display.log_table(console, entries, not display.use_rich(console))

if __name__ == "__main__":
    app()
