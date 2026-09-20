import sys
import typer
from .env import load_dotenv
from .capture import capture_and_run
from .analyze import analyze_log,list_logs
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

@app.command()
def run(
    command: str,
    ai: bool = typer.Option(False, "--ai", help="Use AI enhanced analysis on errors"),
    provider: str = typer.Option(None, "--provider", help=_PROVIDER_HELP),
    model: str = typer.Option(None, "--model", help="Model override. Env: LOGWISE_MODEL."),
):
    """ Run a command: Output normally on success, analyze errors with reasons/fixes """
    capture_and_run(command, use_ai=ai, provider=provider, model=model)

@app.command()
def analyze(
    log_file: str = typer.Argument(..., help="Log file to analyze"),
    ai: bool = typer.Option( False, "--ai", help="Use AI for enchanced analysis"),
    provider: str = typer.Option(None, "--provider", help=_PROVIDER_HELP),
    model: str = typer.Option(None, "--model", help="Model override. Env: LOGWISE_MODEL."),
):
    """
        Analyze a captured log for errors
    """
    result = analyze_log(log_file,use_ai=ai,provider=provider,model=model)
    if 'error' in result:
        typer.echo(result['error'])
        return

    typer.echo("Log Summary:")
    typer.echo(result['summary'])
    for issue in result.get('issues', []):
        typer.echo(f"- Reason: {issue['description']} ({issue['root_cause']})")
        typer.echo(f"  Steps to fix: {issue['fixes']}")
    if 'ai_analysis' in result:
        typer.echo("\nAI Analysis:")
        typer.echo(f"Reason: {result['ai_analysis']['reason']}")
        typer.echo(f"Steps to fix: {result['ai_analysis']['fixes']}")

@app.command()
def list():
    """
    List all captured logs.
    """
    logs = list_logs()
    if not logs:
        typer.echo("No logs found.")
    for log in logs:
        typer.echo(log)

if __name__ == "__main__":
    app()
