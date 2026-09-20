"""Shared helpers: env isolation for LOGWISE_* / provider keys."""

import os

MANAGED_VARS = [
    "LOGWISE_PROVIDER",
    "LOGWISE_MODEL",
    "LOGWISE_BASE_URL",
    "LOGWISE_API_KEY",
    "LOGWISE_LOG_DIR",
    "LOGWISE_ENV_FILE",
    "LOGWISE_NO_COLOR",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
]


def clear_managed_env(testcase):
    """Snapshot managed vars, clear them, restore on cleanup."""
    saved = {k: os.environ.get(k) for k in MANAGED_VARS}
    for k in MANAGED_VARS:
        os.environ.pop(k, None)

    def restore():
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    testcase.addCleanup(restore)
