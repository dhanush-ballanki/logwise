# AGENTS.md — LogWise

Tiny Typer CLI (Python >=3.10) that runs a shell command, saves failures as JSON, and suggests fixes via rules + optional Gemini.

## Entrypoints & layout

- `src/logwise/main.py` — Typer `app`, commands `run | analyze | list`. Installed as `logwise = "logwise.main:app"`.
- `src/logwise/capture.py` — `capture_and_run()`: `subprocess.run(shell=True)`, writes `logs/log_<iso>.json` on failure, prints analysis.
- `src/logwise/analyze.py` — `analyze_log_in_memory()` / `analyze_log()` / `list_logs()`.
- `src/logwise/rules.py` — `ERROR_RULES` + `apply_rules()`. Add new rules as dicts with `id/condition/description/root_cause/fixes`.
- `src/logwise/ai.py` — `ai_analyze_err()` over OpenAI-compatible `POST {base_url}/chat/completions` via stdlib `urllib` only. **No vendor SDKs** (google-genai removed).
- `src/logwise/providers.py` — `PROVIDERS` table `{base_url, key_env, default_model}` + `resolve_*()` (flag → `LOGWISE_*` env → default). New vendors are data-only entries.
- `src/logwise/` has **no `__init__.py`** (namespace package). Do not add one unless packaging requires it.

## Setup / run (uv is canonical)

```bash
uv sync                  # create .venv, install locked deps + editable logwise
uv run logwise run "ls /missing/path"
uv run logwise analyze <filename-inside-logs-dir> [--ai]
uv run logwise list
uv build                 # wheel + sdist into dist/
```

- `pyproject.toml` + `uv.lock` are the source of truth. `requirements.txt` / `Pipfile` are legacy leftovers — don't add new deps there.
- `.python-version` pins 3.12. `typer==0.21.1` (unified; the old `0.12.5` pin broke rich `--help` against new `click`).
- `--ai` needs a key for the chosen provider (`GEMINI_API_KEY` by default; `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, or generic `LOGWISE_API_KEY`). `ollama` is keyless. Overrides: `--provider` / `--model` flags or `LOGWISE_PROVIDER` / `LOGWISE_MODEL` / `LOGWISE_BASE_URL` env. No `.env` loader — export in shell.

## Gotchas (verified in code)

- `LOG_DIR` is `src/logwise/../../logs` (= repo-root `logs/`). Not configurable. `logs/` is gitignored-by-pattern (`*.log` rule won't cover it, but dir doesn't exist in repo).
- `list_logs()` returns `[]` when `logs/` is missing (fixed; it used to crash with `FileNotFoundError`). `analyze` on a missing file returns `{'error': ...}`.
- `capture_and_run` treats `returncode==0 + stderr non-empty` as failure (writes a log). Success prints stdout only.
- `--ai` semantics: `analyze_log_in_memory(use_ai=True)` **skips rules entirely** (AI-only). Default mode runs rules first, falls back to AI only if zero rules match. Don't "fix" this without changing intended UX.
- `ai.py` creates `genai.Client()` lazily inside `ai_analyze_err()` (fixed; it used to be module-level and crashed every command without credentials). Keep it lazy if touching imports.
- No tests, lint, typecheck, formatter, CI, or pre-commit config exist. Verify manually with `logwise run` on a failing + passing command.
