import typer
from .capture import capture_and_run
from .analyze import analyze_log,list_logs

app = typer.Typer(help="LogWise: Intelligent Log Analyzer")

@app.command()
def run(
    command: str,
    ai: bool = typer.Option(False, "--ai", help="Use AI enhanced analysis on errors")
):
    """ Run a command: Output normally on success, analyze errors with reasons/fixes """
    capture_and_run(command, use_ai=ai)

@app.command()
def analyze(
    log_file: str = typer.Argument(..., help="Log file to analyze"),
    ai: bool = typer.Option( False, "--ai", help="Use AI for enchanced analysis"),
):
    """
        Analyze a captured log for errors
    """
    result = analyze_log(log_file,use_ai=ai)
    if 'error' in result:
        typer.echo(result['error'])
        return
    
    typer.echo("Log Summary:")
    typer.echo(result['summary'])
    for issue in result['issues']:
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