"""Minimal `.env` file support (stdlib only, no python-dotenv dependency).

Loaded once at CLI startup (see ``main.py``). Rules:

- Discovery: ``LOGWISE_ENV_FILE`` if set, else the first ``.env`` found
  walking from the current working directory up to the filesystem root.
  (Cwd-based, not package-dir-based, so it works for a pip-installed
  ``logwise`` run from any project directory.)
- Precedence: real process environment always wins — file values are
  applied with ``os.environ.setdefault`` and never override exports.
- Format (common subset): ``KEY=VALUE`` lines, optional ``export ``
  prefix, ``#`` comments, single/double-quote stripping. Single-line
  values only; no variable interpolation or multiline values.

A missing file is silently ignored, except an explicitly-set but
missing ``LOGWISE_ENV_FILE``, which warns on stderr.
"""

import os
import sys
from pathlib import Path

ENV_FILENAME = ".env"
ENV_FILE_OVERRIDE_VAR = "LOGWISE_ENV_FILE"


def find_dotenv(start: Path | None = None) -> Path | None:
    """Return the nearest `.env` from `start` upward, or None."""
    current = (start or Path.cwd()).resolve()
    root = current.anchor
    while True:
        candidate = current / ENV_FILENAME
        if candidate.is_file():
            return candidate
        if str(current) == root:
            return None
        current = current.parent


def parse_dotenv_text(text: str) -> dict:
    """Parse `.env` content into a dict (no env interaction)."""
    values: dict = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key or key[0].isdigit() or not key.replace("_", "").isalnum():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        elif "#" in value:
            # Strip trailing inline comments only for unquoted values.
            value = value.split("#", 1)[0].rstrip()
        values[key] = value
    return values


def load_dotenv(path: Path | str | None = None) -> Path | None:
    """Load environment variables from a `.env` file.

    Returns the path loaded, or None if no file was found. Existing
    process environment variables are never overridden.
    """
    if path is None:
        override = os.getenv(ENV_FILE_OVERRIDE_VAR)
        if override:
            explicit = Path(override).expanduser()
            if not explicit.is_file():
                print(
                    f"logwise: {ENV_FILE_OVERRIDE_VAR}={override} not found, skipping.",
                    file=sys.stderr,
                )
                return None
            path = explicit
        else:
            found = find_dotenv()
            if found is None:
                return None
            path = found
    else:
        path = Path(path).expanduser()
        if not path.is_file():
            return None

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for key, value in parse_dotenv_text(text).items():
        os.environ.setdefault(key, value)
    return path
