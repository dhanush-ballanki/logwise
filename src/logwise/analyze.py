import json
import os

from .paths import get_log_dir
from .rules import apply_rules


def analyze_log_in_memory(
    log: dict, use_ai: bool = False, provider: str | None = None, model: str | None = None
) -> dict:
    """
    Analyze log dict directly.
    If use_ai=True → AI-only analysis (rules skipped)
    """
    result = {"log": log}

    # --- AI MODE (explicit override) ---
    if use_ai:
        from .ai import ai_analyze_err  # lazy: no network imports unless needed

        ai_result = ai_analyze_err(
            log["command"],
            log["stderr"],
            log["exit_code"],
            provider=provider,
            model=model,
        )
        if "error" in ai_result:
            result["summary"] = f"AI analysis failed: {ai_result['error']}"
        else:
            result["summary"] = "AI-based analysis requested."
            result["ai_analysis"] = ai_result
        return result

    # --- DEFAULT MODE (rules first, AI fallback) ---
    issues = apply_rules(log)
    result["issues"] = issues

    if issues:
        result["summary"] = f"Found {len(issues)} rule-based issue(s)."
        return result

    from .ai import ai_analyze_err  # lazy: no network imports unless needed

    ai_result = ai_analyze_err(
        log["command"],
        log["stderr"],
        log["exit_code"],
        provider=provider,
        model=model,
    )
    if "error" in ai_result:
        result["summary"] = f"No rule-based issues. AI fallback failed: {ai_result['error']}"
    else:
        result["summary"] = "No rule-based issues. AI fallback used."
        result["ai_analysis"] = ai_result

    return result


def analyze_log(
    log_file: str, use_ai: bool = False, provider: str | None = None, model: str | None = None
) -> dict:
    full_path = os.path.join(get_log_dir(), log_file)
    if not os.path.exists(full_path):
        return {"error": "Log file not found."}

    with open(full_path) as f:
        log = json.load(f)

    return analyze_log_in_memory(log, use_ai=use_ai, provider=provider, model=model)


def list_logs() -> list:
    log_dir = get_log_dir()
    if not os.path.isdir(log_dir):
        return []
    return [f for f in os.listdir(log_dir) if f.endswith(".json")]


def prune_logs(
    keep: int | None = None, older_than_days: float | None = None, dry_run: bool = False
) -> dict:
    """Delete saved logs by age/count.

    Returns {"deleted": [...], "kept": n}; with `dry_run=True` nothing is
    removed and the doomed files are reported under "doomed" instead.

    - `older_than_days` set: only files older than that are eligible.
    - `keep` set: the newest `keep` eligible files are exempt.
    - Both None: nothing is deleted.
    Files are ordered by mtime (oldest first). Unreadable/deleted files
    are skipped, never fatal.
    """
    if keep is None and older_than_days is None:
        return {"deleted": [], "doomed": [], "kept": len(list_logs())}
    log_dir = get_log_dir()
    entries = []
    for name in list_logs():
        try:
            entries.append((os.path.getmtime(os.path.join(log_dir, name)), name))
        except OSError:
            continue
    entries.sort()  # oldest first
    if older_than_days is not None:
        import time

        cutoff = time.time() - older_than_days * 86400
        entries = [(mtime, name) for mtime, name in entries if mtime < cutoff]
    doomed = [name for _, name in entries]
    if keep is not None and keep >= 0:
        doomed = doomed[: max(0, len(doomed) - keep)]
    if dry_run:
        return {"deleted": [], "doomed": doomed, "kept": len(list_logs())}
    deleted = []
    for name in doomed:
        try:
            os.remove(os.path.join(log_dir, name))
            deleted.append(name)
        except OSError:
            continue
    return {"deleted": deleted, "doomed": [], "kept": len(list_logs())}
