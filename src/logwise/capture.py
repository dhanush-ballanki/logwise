import subprocess
import os
import datetime
import json
from .analyze import analyze_log_in_memory


LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../logs')

def capture_and_run(command: str, use_ai: bool = False) -> None:
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
            os.makedirs(LOG_DIR, exist_ok=True)
            log_file = os.path.join(LOG_DIR, f"log_{start_time.replace(':','-')}.json")
            with open(log_file, 'w') as f:
                json.dump(log_entry, f, indent=4)
            # Analyze in memory
            analysis = analyze_log_in_memory(log_entry, use_ai=use_ai)
            print(f"Error occurred (exit code: {result.returncode})")
            print("Stderr captured:")
            print(result.stderr)
            print("\nAnalysis:")
            print(analysis['summary'])
            for issue in analysis['issues']:
                print(f"- Reason: {issue['description']} ({issue['root_cause']})")
                print(f"  Steps to fix: {issue['fixes']}")
            if 'ai_analysis' in analysis:
                print("\nAI Enhanced Analysis:")
                print(f"Reason: {analysis['ai_analysis']['reason']}")
                print(f"Steps to fix: {analysis['ai_analysis']['fixes']}")

    except Exception as e:
        print('Execution failed: '+str(e))