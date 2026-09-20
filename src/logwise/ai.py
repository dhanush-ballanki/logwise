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

Reply in exactly this format, under 200 words:
Reason: <one or two plain-language sentences>
Fixes:
1. <first step>
2. <second step>
"""


def _extract_sse_content(body: str) -> str:
    """Assemble assistant text from a Server-Sent Events stream.

    Some OpenAI-compatible servers stream even when asked not to.
    Collects ``choices[0].delta.content`` from each ``data:`` chunk,
    ignoring reasoning fields and the ``[DONE]`` terminator.
    """
    parts = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            chunk = json.loads(data)
        except ValueError:
            continue
        try:
            delta = chunk["choices"][0].get("delta", {})
        except (KeyError, IndexError, AttributeError):
            continue
        content = delta.get("content")
        if content:
            parts.append(content)
    return "".join(parts).strip()


def _post_chat_completions(base_url: str, api_key: str | None, model: str, prompt: str) -> str:
    """POST one chat-completions request, return the assistant text."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 700,
        "stream": False,
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
            raw = resp.read().decode("utf-8", "replace")
            content_type = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {e.code} from {base_url}: {detail}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cannot reach {base_url}: {e.reason}")

    if "text/event-stream" in content_type:
        text = _extract_sse_content(raw)
        if not text:
            raise RuntimeError(f"Empty SSE stream from {base_url}. Preview: {raw[:300]}")
        return text
    try:
        payload = json.loads(raw)
    except ValueError:
        raise RuntimeError(
            f"Non-JSON response from {base_url} "
            f"(content-type: {content_type or 'unknown'}). "
            f"Preview: {raw[:300]}"
        )
    try:
        return payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError):
        raise RuntimeError(f"Unexpected API response shape: {str(payload)[:300]}")


#: Line markers (case-insensitive, markdown-bold tolerant) that start
#: the fixes section of a model response.
_FIXES_MARKERS = (
    "step-by-step",
    "steps to fix",
    "fix steps",
    "how to fix",
    "fixes:",
    "solution:",
    "resolution:",
)


def _split_reason_fixes(analysis: str) -> tuple[str, str]:
    """Split model output into (reason, fixes).

    Finds the first line starting with a known fixes marker; everything
    before it is the reason (minus a leading ``Reason:`` label), everything
    from it onward is the fixes (minus a bare header line like
    ``**Fix Steps:**``). Falls back to whole-text-as-reason.
    """
    lines = analysis.splitlines()
    for i, line in enumerate(lines):
        clean = line.strip().strip("*").strip().lower()
        if not any(clean.startswith(m) for m in _FIXES_MARKERS):
            continue
        reason = "\n".join(lines[:i])
        for label in ("a simple human-readable reason for the error:", "reason:"):
            bare = reason.lstrip().lstrip("*")
            if bare.lower().startswith(label):
                reason = bare[len(label) :].lstrip("*").strip()
                break
        fix_lines = lines[i:]
        if fix_lines[0].strip().strip("*").strip().endswith(":"):
            fix_lines = fix_lines[1:]  # bare header line, drop it
        fixes = "\n".join(fix_lines).strip()
        return reason.strip(), fixes or "No fixes suggested."
    return analysis.strip(), "No fixes suggested."


def ai_analyze_err(
    command: str, stderr: str, exit_code: int, provider: str | None = None, model: str | None = None
) -> dict:
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

    keyless_local = "localhost" in base_url or "127.0.0.1" in base_url
    if config["key_env"] is not None and not api_key and not keyless_local:
        return {"error": f"No API key for provider '{canonical}'. {key_hint(canonical, config)}."}

    prompt = _PROMPT_TEMPLATE.format(command=command, exit_code=exit_code, stderr=stderr)
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
