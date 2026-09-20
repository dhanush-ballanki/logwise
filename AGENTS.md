# AGENTS.md — LogWise

Tiny Typer CLI (Python >=3.10) that runs a shell command, saves failures as JSON, and suggests fixes via rules + optional Gemini.

## Entrypoints & layout

- `src/logwise/main.py` — Typer `app`, commands `run | analyze | list`. Installed as `logwise = "logwise.main:app"`.
- `src/logwise/capture.py` — `capture_and_run()`: `subprocess.run(shell=True)`, writes `logs/log_<iso>.json` on failure, prints analysis.
- `src/logwise/analyze.py` — `analyze_log_in_memory()` / `analyze_log()` / `list_logs()`.
- `src/logwise/rules.py` — `ERROR_RULES` + `apply_rules()`. Add new rules as dicts with `id/condition/description/root_cause/fixes`.
- `src/logwise/ai.py` — `ai_analyze_err()` over OpenAI-compatible `POST {base_url}/chat/completions` via stdlib `urllib` only. **No vendor SDKs** (google-genai removed).
- `src/logwise/providers.py` — `PROVIDERS` table `{base_url, key_env, default_model}` + `resolve_*()` (flag → `LOGWISE_*` env → default). New vendors are data-only entries.
- `src/logwise/env.py` — stdlib `.env` loader (`load_dotenv()`; `LOGWISE_ENV_FILE` or nearest `.env` upward from cwd; real env always wins). Called once in `main.py`.
- `src/logwise/paths.py` — `get_log_dir()` (`LOGWISE_LOG_DIR` or `cwd/logs`). Never write runtime data relative to `__file__` (breaks pip installs).
- `src/logwise/` has **no `__init__.py`** (namespace package). Do not add one unless packaging requires it.

## Setup / run (uv is canonical)

```bash
uv sync                  # create .venv, install locked deps + editable logwise
uv run logwise run "ls /missing/path"
uv run logwise analyze <filename-inside-logs-dir> [--ai]
uv run logwise list
uv build                 # wheel + sdist into dist/
```

- `pyproject.toml` + `uv.lock` are the source of truth for deps.
- `.python-version` pins 3.12. `typer==0.21.1` (unified; the old `0.12.5` pin broke rich `--help` against new `click`).
- `--ai` needs a key for the chosen provider (`GEMINI_API_KEY` by default; `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, or generic `LOGWISE_API_KEY`). `ollama` is keyless. Overrides: `--provider` / `--model` flags or `LOGWISE_PROVIDER` / `LOGWISE_MODEL` / `LOGWISE_BASE_URL` env. `.env` is auto-loaded (see `env.py`); exports beat file values.
- PyPI-ready: single runtime dep (`typer`), SPDX license, classifiers + urls in `pyproject.toml`. Bump `version` per release; never commit `.env` or `dist/`.

## Gotchas (verified in code)

- Log dir is cwd-based: `get_log_dir()` = `LOGWISE_LOG_DIR` or `cwd/logs` (was `__file__`-relative; that breaks pip installs by writing into `site-packages`). `list_logs()` returns `[]` when missing. `analyze` on a missing file returns `{'error': ...}`.
- `capture_and_run` treats `returncode==0 + stderr non-empty` as failure (writes a log). Success prints stdout only.
- `--ai` semantics: `analyze_log_in_memory(use_ai=True)` **skips rules entirely** (AI-only). Default mode runs rules first, falls back to AI only if zero rules match. Don't "fix" this without changing intended UX.
- `ai.py` is stdlib-only (`urllib`); the AI import in `analyze.py` is lazy so non-AI commands never touch networking. Keep both that way.
- No tests, lint, typecheck, formatter, CI, or pre-commit config exist. Verify manually with `logwise run` on a failing + passing command.
