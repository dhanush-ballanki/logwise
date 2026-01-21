import os
import json
from .rules import apply_rules
from .ai import ai_analyze_err

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../logs')

def analyze_log_in_memory(log: dict, use_ai: bool = False) -> dict:
    """
    Analyze log dict directly.
    If use_ai=True → AI-only analysis (rules skipped)
    """
    result = {'log': log}

    # --- AI MODE (explicit override) ---
    if use_ai:
        ai_result = ai_analyze_err(
            log['command'],
            log['stderr'],
            log['exit_code']
        )
        result['summary'] = "AI-based analysis requested."
        if 'error' not in ai_result:
            result['ai_analysis'] = ai_result
        return result

    # --- DEFAULT MODE (rules first, AI fallback) ---
    issues = apply_rules(log)
    result['issues'] = issues

    if issues:
        result['summary'] = f"Found {len(issues)} rule-based issue(s)."
        return result

    ai_result = ai_analyze_err(
        log['command'],
        log['stderr'],
        log['exit_code']
    )
    result['summary'] = "No rule-based issues. AI fallback used."
    if 'error' not in ai_result:
        result['ai_analysis'] = ai_result

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