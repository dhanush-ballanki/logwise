import os
import json
from .rules import apply_rules
from .ai import ai_analyze_error

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../logs')

def analyze_log_in_memory(log: dict, use_ai: bool = False) -> dict:
    """
    Analyze log dict directly.
    """
    issues = apply_rules(log)
    
    result = {
        'log': log,
        'issues': issues,
        'summary': f"Found {len(issues)} issues." if issues else "No issues detected."
    }
    
    if use_ai or not issues:  # Use AI if requested or no rules matched
        ai_result = ai_analyze_error(log['command'], log['stderr'], log['exit_code'])
        if 'error' not in ai_result:
            result['ai_analysis'] = ai_result
            if not issues:
                result['summary'] = "No rule-based issues, but AI analysis provided."
    
    return result

def analyze_log(log_file: str, use_ai: bool = False) -> dict:
    full_path = os.path.join(LOG_DIR, log_file)
    if not os.path.exists(full_path):
        return {'error': 'Log file not found.'}
    
    with open(full_path, 'r') as f:
        log = json.load(f)
    
    return analyze_log_in_memory(log, use_ai=use_ai)

def list_logs() -> list:
    return [f for f in os.listdir(LOG_DIR) if f.endswith('.json')]