"""Filesystem locations for LogWise runtime data.

``get_log_dir()`` resolves per call (not at import time) so library users
and tests that change cwd get the right directory.

Resolution: ``LOGWISE_LOG_DIR`` env var, else ``logs/`` under the current
working directory. Cwd-based (not package-dir-based): a pip-installed
``logwise`` must never write into ``site-packages``.
"""

import os
from pathlib import Path


def get_log_dir() -> Path:
    """Return the directory where failure logs are stored."""
    override = os.getenv("LOGWISE_LOG_DIR")
    if override:
        return Path(override).expanduser()
    return Path.cwd() / "logs"


def ensure_log_dir() -> Path:
    """Best-effort creation of the log dir (never raises).

    Called once at CLI startup so `list` works before any failure.
    Read-only locations are silently ignored — commands cope already.
    """
    log_dir = get_log_dir()
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return log_dir
