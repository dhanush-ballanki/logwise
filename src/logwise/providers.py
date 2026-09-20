"""Provider registry for LogWise AI analysis.

Every provider here speaks the OpenAI-compatible
``POST {base_url}/chat/completions`` API — including Gemini (via its
OpenAI-compat endpoint) and local servers like Ollama. Adding a new
vendor is data-only: one dict entry, zero new dependencies.
"""

import os

PROVIDERS = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_env": "GEMINI_API_KEY",
        "default_model": "gemini-2.0-flash",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "default_model": "openai/gpt-4o-mini",
    },
    # Local, keyless. Requires `ollama serve` + a pulled model.
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "key_env": None,
        "default_model": "llama3.1",
    },
}

DEFAULT_PROVIDER = "gemini"


def resolve_provider(name: str | None) -> tuple[str, dict]:
    """Return (canonical_name, config). Raises ValueError on unknown name."""
    raw = (name or os.getenv("LOGWISE_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    if raw not in PROVIDERS:
        raise ValueError(
            f"Unknown provider '{raw}'. Valid options: {', '.join(sorted(PROVIDERS))}."
        )
    return raw, PROVIDERS[raw]


def resolve_model(config: dict, model: str | None) -> str:
    """CLI flag → LOGWISE_MODEL env → provider default."""
    return (model or os.getenv("LOGWISE_MODEL") or config["default_model"]).strip()


def resolve_base_url(config: dict) -> str:
    """LOGWISE_BASE_URL env overrides the provider default (custom servers)."""
    return (os.getenv("LOGWISE_BASE_URL") or config["base_url"]).rstrip("/")


def resolve_api_key(canonical_name: str, config: dict) -> str | None:
    """LOGWISE_API_KEY env overrides the provider-specific key env.

    Returns None for keyless providers (e.g. ollama) or when no key is set
    (caller turns that into a clean error message).
    """
    if config["key_env"] is None:
        return os.getenv("LOGWISE_API_KEY")  # optional even for local servers
    return os.getenv("LOGWISE_API_KEY") or os.getenv(config["key_env"])


def key_hint(canonical_name: str, config: dict) -> str:
    """Human-readable hint for the missing-key error message."""
    if config["key_env"] is None:
        return "no API key needed (local server)"
    return f"Set env var {config['key_env']} (or generic LOGWISE_API_KEY)"
