import os
import json
from .rules import apply_rules
from .paths import get_log_dir

def analyze_log_in_memory(log: dict, use_ai: bool = False,
                          provider: str | None = None,
                          model: str | None = None) -> dict:
    """
    Analyze log dict directly.
    If use_ai=True → AI-only analysis (rules skipped)
    """
    result = {'log': log}

    # --- AI MODE (explicit override) ---
    if use_ai:
        from .ai import ai_analyze_err  # lazy: no network imports unless needed
        ai_result = ai_analyze_err(
            log['command'],
            log['stderr'],
            log['exit_code'],
            provider=provider,
            model=model,
        )
        if 'error' in ai_result:
            result['summary'] = f"AI analysis failed: {ai_result['error']}"
        else:
            result['summary'] = "AI-based analysis requested."
            result['ai_analysis'] = ai_result
        return result

    # --- DEFAULT MODE (rules first, AI fallback) ---
    issues = apply_rules(log)
    result['issues'] = issues

    if issues:
        result['summary'] = f"Found {len(issues)} rule-based issue(s)."
        return result

    from .ai import ai_analyze_err  # lazy: no network imports unless needed
    ai_result = ai_analyze_err(
        log['command'],
        log['stderr'],
        log['exit_code'],
        provider=provider,
        model=model,
    )
    if 'error' in ai_result:
        result['summary'] = f"No rule-based issues. AI fallback failed: {ai_result['error']}"
    else:
        result['summary'] = "No rule-based issues. AI fallback used."
        result['ai_analysis'] = ai_result

    return result


def analyze_log(log_file: str, use_ai: bool = False,
                provider: str | None = None,
                model: str | None = None) -> dict:
    full_path = os.path.join(get_log_dir(), log_file)
    if not os.path.exists(full_path):
        return {'error': 'Log file not found.'}

    with open(full_path, 'r') as f:
        log = json.load(f)

    return analyze_log_in_memory(log, use_ai=use_ai,
                                 provider=provider, model=model)

def list_logs() -> list:
    log_dir = get_log_dir()
    if not os.path.isdir(log_dir):
        return []
    return [f for f in os.listdir(log_dir) if f.endswith('.json')]