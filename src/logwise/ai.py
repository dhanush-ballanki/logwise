"""AI error analysis over any OpenAI-compatible chat API.

Single HTTP code path (stdlib ``urllib`` only — no vendor SDKs) for all
providers in :mod:`logwise.providers`. Gemini works through its
``.../v1beta/openai`` endpoint; Ollama/LM Studio work against localhost.
"""

import json
import urllib.error
import urllib.request

from .providers import (
    PROVIDERS,
    key_hint,
    resolve_api_key,
    resolve_base_url,
    resolve_model,
    resolve_provider,
)

TIMEOUT_S = 30

_PROMPT_TEMPLATE = """Analyze this command error:
Command: {command}
Exit code: {exit_code}
Stderr: {stderr}

Provide:
- A simple human-readable reason for the error.
- Step-by-step instructions to fix it.
Keep it concise, under 200 words.
"""


def _post_chat_completions(base_url: str, api_key: str | None,
                           model: str, prompt: str) -> str:
    """POST one chat-completions request, return the assistant text."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 700,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {e.code} from {base_url}: {detail}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cannot reach {base_url}: {e.reason}")
    try:
        return payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError):
        raise RuntimeError(f"Unexpected API response shape: {str(payload)[:300]}")


def _split_reason_fixes(analysis: str) -> tuple[str, str]:
    """Tolerantly split model output into (reason, fixes)."""
    lowered = analysis.lower()
    marker = "step-by-step"
    idx = lowered.find(marker)
    if idx == -1:
        return analysis.strip(), "No fixes suggested."
    # Split at the start of the line containing the marker.
    line_start = analysis.rfind("\n", 0, idx) + 1
    reason = analysis[:line_start]
    fixes = analysis[line_start:]
    for label in ("a simple human-readable reason for the error:",
                  "reason:"):
        if reason.lower().lstrip().startswith(label):
            reason = reason.lstrip()[len(label):]
            break
    # Drop the marker line itself from fixes ("Step-by-step ...:" header).
    first_nl = fixes.find("\n")
    if first_nl != -1 and "step-by-step" in fixes[:first_nl].lower():
        fixes = fixes[first_nl + 1:]
    return reason.strip(), fixes.strip() or "No fixes suggested."


def ai_analyze_err(command: str, stderr: str, exit_code: int,
                   provider: str | None = None,
                   model: str | None = None) -> dict:
    """
    Analyze an error with the selected provider (default: gemini).

    Returns {"reason", "fixes", "provider", "model"} or {"error": ...}.
    Resolves provider → LOGWISE_PROVIDER env → "gemini";
    model → LOGWISE_MODEL env → provider default;
    key → LOGWISE_API_KEY env → provider key env.
    """
    try:
        canonical, config = resolve_provider(provider)
    except ValueError as e:
        return {"error": str(e)}
    use_model = resolve_model(config, model)
    base_url = resolve_base_url(config)
    api_key = resolve_api_key(canonical, config)

    if config["key_env"] is not None and not api_key and "localhost" not in base_url and "127.0.0.1" not in base_url:
        return {"error": f"No API key for provider '{canonical}'. {key_hint(canonical, config)}."}

    prompt = _PROMPT_TEMPLATE.format(
        command=command, exit_code=exit_code, stderr=stderr)
    try:
        analysis = _post_chat_completions(base_url, api_key, use_model, prompt)
    except Exception as e:
        return {"error": f"AI analysis failed ({canonical}/{use_model}): {e}"}

    reason, fixes = _split_reason_fixes(analysis)
    return {
        "reason": reason,
        "fixes": fixes,
        "provider": canonical,
        "model": use_model,
    }


def list_providers() -> list:
    """Provider names for CLI help / validation."""
    return sorted(PROVIDERS)
