import subprocess
import os
import datetime
import json
from .analyze import analyze_log_in_memory
from . import display
from .paths import get_log_dir

def capture_and_run(command: str, use_ai: bool = False,
                    provider: str | None = None,
                    model: str | None = None,
                    no_color: bool = False) -> None:
    """
        Run command, print output if no error else analyze the error
    """
    start_time = datetime.datetime.now().isoformat()
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        log_entry = {
            'command' : command,
            'start_time' : start_time,
            'end_time' : datetime.datetime.now().isoformat(),
            'stdout' : result.stdout.strip(),
            'stderr' : result.stderr.strip(),
            'exit_code' : result.returncode,
        }
        if result.returncode == 0 and not result.stderr:
            print(result.stdout)
        else:
            log_dir = get_log_dir()
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"log_{start_time.replace(':','-')}.json")
            with open(log_file, 'w') as f:
                json.dump(log_entry, f, indent=4)
            # Analyze in memory
            analysis = analyze_log_in_memory(log_entry, use_ai=use_ai,
                                             provider=provider, model=model)
            console = display.get_console(no_color=no_color)
            plain = not display.use_rich(console)
            display.error_header(console, result.returncode, plain)
            display.stderr_block(console, result.stderr, plain)
            display.analysis(console, analysis['summary'],
                             analysis.get('issues', []),
                             analysis.get('ai_analysis'), plain)

    except Exception as e:
        print('Execution failed: '+str(e))