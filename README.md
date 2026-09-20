# LogWise

LogWise is a lightweight Python CLI that runs shell commands, saves failures as JSON logs, detects common failure patterns with built-in rules, and optionally asks an AI provider to explain the error and suggest fixes.

## Why LogWise?

When a command fails, the usual workflow is: rerun it, squint at the output, guess the root cause. LogWise shortens that loop by:

- running commands through a simple CLI,
- capturing stdout, stderr, exit codes, and timestamps,
- persisting every failure as a JSON log for later inspection,
- matching failures against built-in rules (missing files, permissions, …),
- suggesting practical fixes immediately,
- optionally consulting an AI provider — Gemini, OpenAI, DeepSeek, Groq, OpenRouter, or a local Ollama — through a single SDK-free HTTP layer.

## Features

- `run` — execute a command; print stdout on success, log + analyze on failure
- `analyze` — re-analyze any saved log file
- `list` — list saved logs as a table (file, command, exit code)
- `prune` — delete old logs by count (`--keep`) and/or age (`--older-than`), asks first unless `--yes`
- Interactive retry / AI-offer / rerun prompts on terminals (off when piped; `--no-prompt` / `LOGWISE_NO_PROMPT`)
- Rule engine with extensible `ERROR_RULES`
- Multi-provider AI analysis over OpenAI-compatible APIs (stdlib `urllib` only, zero vendor SDKs), with spinner + per-provider accent colors
- Rich terminal output with byte-identical plain fallback for pipes (`--no-color`, `NO_COLOR`, `LOGWISE_NO_COLOR`)
- `uv`-managed project: locked deps, reproducible builds
- stdlib `unittest` suite (`tests/`), Ruff lint + format, CI workflow

## Requirements

- Python 3.10+ (`.python-version` pins 3.12)
- [`uv`](https://docs.astral.sh/uv/) for install/build (recommended)
- A terminal environment
- Optional: an API key for your AI provider (see [AI analysis](#ai-analysis)); `ollama` needs no key

## Installation

```bash
git clone https://github.com/dhanush-ballanki/logwise.git
cd logwise
uv sync          # create .venv, install locked deps + editable logwise
```

Run via `uv run`, or activate the venv (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on Unix) and use `logwise` directly:

```bash
uv run logwise run "python script.py"
```

Build distributables (wheel + sdist into `dist/`):

```bash
uv build
```

Prefer plain pip? `pyproject.toml` is standards-based, so this works too:

```bash
python -m venv .venv
pip install -e .
```

## Usage

### Run a command

```bash
logwise run "python script.py"
```

Success prints stdout only. Failure saves `logs/log_<timestamp>.json` and prints the analysis.

```bash
logwise run "python script.py" --ai --provider openai --model gpt-4o-mini
```

### Analyze an existing log

```bash
logwise analyze log_2025-04-06T10-30-00.json
logwise analyze log_2025-04-06T10-30-00.json --ai --provider groq
```

### List captured logs

```bash
logwise list
```

### Prune old logs

```bash
logwise prune --keep 50              # keep newest 50, preview + confirm
logwise prune --keep 20 --older-than 30 --yes   # ...older than 30 days, no prompt
```

### Example

```bash
logwise run "ls /missing/path"
```

```text
Error occurred (exit code: 2)
Stderr captured:
ls: cannot access '/missing/path': No such file or directory

Analysis:
Found 2 rule-based issue(s).
- Reason: Command failed with non-zero exit code. (Possible reasons: Invalid arguments, missing dependencies, or runtime errors. Check stderr for details.)
  Steps to fix: Verify command syntax, install missing packages, or debug the script.
- Reason: File or directory not found. (Path issue.)
  Steps to fix: Check if the file exists (ls), correct the path, or create the missing item.
```

## Output & colors

On a real terminal, failures render with Rich: a red `❌ Error` header, stderr in a red panel, yellow `⚠` issue rows with green `→` fixes, and AI advice as a Markdown panel captioned with `provider / model` in that provider's accent color (blue Gemini, green OpenAI, violet DeepSeek, orange Groq, cyan OpenRouter, grey Ollama). `list` renders a table (file, command, exit code).

Plain text is automatic when output is piped or redirected, and can be forced with `--no-color`, `NO_COLOR=1`, or `LOGWISE_NO_COLOR=1`. Successful command stdout is never styled — it stays byte-identical so pipes and scripts keep working.

On terminals, `run` offers to retry a failed command (and to analyze with AI if you didn't pass `--ai`), and `analyze` offers to re-run the logged command. Prompts never appear when piped; `--no-prompt` / `LOGWISE_NO_PROMPT=1` disables them.

## Architecture

### System overview

```mermaid
flowchart LR
    subgraph CLI["CLI (main.py)"]
        RUN["run"]
        ANALYZE["analyze"]
        LIST["list"]
    end

    subgraph CORE["Core"]
        CAP["capture.py\ncapture_and_run()"]
        ANZ["analyze.py\nanalyze_log_in_memory()"]
        RULES["rules.py\napply_rules()"]
    end

    subgraph AILAYER["AI layer (SDK-free)"]
        AI["ai.py\nai_analyze_err()"]
        PROV["providers.py\nPROVIDERS table"]
    end

    STORE[("logs/\nlog_<iso>.json")]

    RUN --> CAP
    ANALYZE --> ANZ
    LIST --> STORE
    CAP --> STORE
    CAP --> ANZ
    ANZ --> RULES
    ANZ --> AI
    AI --> PROV
    AI --> EXT[("AI APIs\nOpenAI-compatible\n/chat/completions")]
```

**Module responsibilities:**

| Module | Role |
| --- | --- |
| `main.py` | Typer `app` with `run` / `analyze` / `list` commands; owns `--ai`, `--provider`, `--model` flags |
| `capture.py` | Runs the command via `subprocess.run(shell=True)`; writes the JSON log on failure; prints the analysis |
| `analyze.py` | `analyze_log_in_memory()` — the analysis orchestrator; `analyze_log()` loads a file then delegates; `list_logs()` lists `logs/` |
| `rules.py` | `ERROR_RULES` list + `apply_rules()`; new rules are plain dicts |
| `ai.py` | One `POST {base_url}/chat/completions` call via stdlib `urllib`; tolerant reason/fixes parsing |
| `providers.py` | `PROVIDERS` table (`base_url`, `key_env`, `default_model`) + `resolve_*()` helpers; adding a vendor is data-only |

`src/logwise/` has no `__init__.py` (namespace package).

### `logwise run` lifecycle

```mermaid
sequenceDiagram
    participant U as User
    participant CLI as main.py run
    participant CAP as capture_and_run
    participant FS as logs/
    participant ANZ as analyze_log_in_memory

    U->>CLI: logwise run "cmd" [--ai]
    CLI->>CAP: capture_and_run(cmd, use_ai, provider, model)
    CAP->>CAP: subprocess.run(shell=True)
    alt exit 0 and empty stderr
        CAP->>U: print(stdout)
    else failure
        CAP->>FS: write log_<iso>.json
        CAP->>ANZ: analyze_log_in_memory(entry, ...)
        ANZ->>U: via CAP: summary + issues + ai_analysis
    end
```

> Quirk: `returncode == 0` **with non-empty stderr** counts as failure and writes a log.

### Analysis decision flow

```mermaid
flowchart TD
    START(["analyze_log_in_memory(log, use_ai)"]) --> ISAI{use_ai?}
    ISAI -- yes --> AIONLY["ai_analyze_err()\n(rules skipped)"]
    AIONLY --> S1["summary = 'AI-based analysis requested.'\nor 'AI analysis failed: ...'"]
    ISAI -- no --> RULES["apply_rules()"]
    RULES --> HIT{issues?}
    HIT -- yes --> S2["summary = 'Found N rule-based issue(s).'"]
    HIT -- no --> FB["ai_analyze_err() fallback"]
    FB --> S3["summary = 'No rule-based issues. AI fallback used.'\nor '... AI fallback failed: ...'"]
```

`--ai` is **AI-only** (rules skipped). Default mode runs rules first and calls AI only when zero rules match. AI errors are surfaced in `summary` — never silent, never a traceback.

### AI layer: one HTTP path, N providers

```mermaid
flowchart LR
    AI["ai_analyze_err()\nresolves provider/model/key"] --> HTTP["_post_chat_completions()\nurllib POST\n{base_url}/chat/completions"]
    HTTP --> GEM["Gemini\n.../v1beta/openai"]
    HTTP --> OAI["OpenAI"]
    HTTP --> DS["DeepSeek"]
    HTTP --> GR["Groq"]
    HTTP --> OR["OpenRouter"]
    HTTP --> OL["Ollama\nlocalhost:11434"]
```

Request shape: `{model, messages: [{role: user, content: prompt}], temperature: 0.7, max_tokens: 700}`, with `Authorization: Bearer <key>` when the provider needs one. The response text is split into `reason` / `fixes` on the `step-by-step` marker (case-insensitive, tolerant of missing headers).

### Resolution precedence

```mermaid
flowchart LR
    F["CLI flag\n--provider / --model"] --> E["Env\nLOGWISE_*"] --> D["Provider default"]
```

| Setting | Flag | Env | Default |
| --- | --- | --- | --- |
| Provider | `--provider` | `LOGWISE_PROVIDER` | `gemini` |
| Model | `--model` | `LOGWISE_MODEL` | provider's `default_model` |
| Base URL | — | `LOGWISE_BASE_URL` | provider's `base_url` |
| API key | — | `LOGWISE_API_KEY` then provider key env | error unless keyless/localhost |

## Log format

Each failure is stored as `logs/log_<ISO-timestamp>.json` (`LOG_DIR` is `src/logwise/../../logs`, i.e. repo-root `logs/`, not configurable):

```json
{
    "command": "ls /missing/path",
    "start_time": "2026-09-20T06:49:37.422836",
    "end_time": "2026-09-20T06:49:37.435101",
    "stdout": "",
    "stderr": "ls: cannot access '/missing/path': No such file or directory",
    "exit_code": 2
}
```

And `analyze_log_in_memory()` returns:

```python
{
    "log": {...},                          # the entry above
    "issues": [...],                       # rule hits (default mode only)
    "summary": "Found 2 rule-based issue(s).",
    "ai_analysis": {                       # only on AI success
        "reason": "...", "fixes": "...",
        "provider": "groq", "model": "llama-3.3-70b-versatile",
    },
}
```

## Rule-based detection

`src/logwise/rules.py` currently ships three rules:

- `non_zero_exit` — exit code ≠ 0
- `permission_denied` — `permission denied` in stderr
- `file_not_found` — `no such file or directory` in stderr

Add a rule as a dict — no framework, no registration calls:

```python
{
    'id': 'module_not_found',
    'condition': lambda log: 'modulenotfounderror' in log['stderr'].lower().replace(' ', ''),
    'description': 'Python module not found.',
    'root_cause': 'Missing dependency.',
    'fixes': 'Install it with pip (pip install <package>).'
}
```

## AI analysis

When `--ai` is used, LogWise sends the command, exit code, and stderr to the selected provider and returns a concise reason plus fix steps.

Available providers (`--provider`, or `LOGWISE_PROVIDER` env, default `gemini`):

| Provider | Key env | Default model |
| --- | --- | --- |
| `gemini` | `GEMINI_API_KEY` | `gemini-2.0-flash` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| `openrouter` | `OPENROUTER_API_KEY` | `openai/gpt-4o-mini` |
| `ollama` | none (local) | `llama3.1` |

```bash
export GEMINI_API_KEY="your_key_here"   # or OPENAI_API_KEY / GROQ_API_KEY / ...
logwise run "python script.py" --ai
logwise run "python script.py" --ai --provider openai --model gpt-4o-mini
logwise analyze log_....json --ai --provider groq
ollama serve & logwise run "python script.py" --ai --provider ollama
```

Generic overrides for any OpenAI-compatible server: `LOGWISE_API_KEY`,
`LOGWISE_MODEL`, `LOGWISE_BASE_URL`. All of these — plus the provider keys —
can live in `.env` instead of exports (see [Installation](#installation)).

## Configuration reference

| Env var | Purpose | Default |
| --- | --- | --- |
| `LOGWISE_PROVIDER` | AI provider name | `gemini` |
| `LOGWISE_MODEL` | Model override | provider default |
| `LOGWISE_BASE_URL` | Custom OpenAI-compatible endpoint | provider default |
| `LOGWISE_API_KEY` | Generic key (beats provider-specific env) | — |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` | Provider keys | — |
| `LOGWISE_ENV_FILE` | Explicit `.env` path (skips upward search) | nearest `.env` from cwd upward |
| `LOGWISE_LOG_DIR` | Where failure logs are stored | `logs/` under cwd |
| `LOGWISE_NO_COLOR` / `NO_COLOR` | Force plain-text output | color when attached to a terminal |

Flags beat env vars: `--provider` > `LOGWISE_PROVIDER`, `--model` > `LOGWISE_MODEL`.
File beats nothing: exported variables always win over `.env` values.

## Project structure

```text
logwise/
├── .github/workflows/      # CI: ruff + unittest + build
├── AGENTS.md
├── LICENSE
├── README.md
├── pyproject.toml          # deps + build config (setuptools, src layout)
├── uv.lock                 # locked deps (committed)
├── .python-version         # pins 3.12
├── src/
│   └── logwise/
│       ├── ai.py           # SDK-free chat-completions client
│       ├── analyze.py      # analysis orchestrator + prune_logs()
│       ├── capture.py      # subprocess runner + log writer
│       ├── display.py      # Rich terminal rendering (only color-aware module)
│       ├── env.py          # stdlib .env loader (no extra dependency)
│       ├── main.py         # Typer CLI (run | analyze | list | prune)
│       ├── paths.py        # runtime data dirs (cwd-based, install-safe)
│       ├── providers.py    # provider registry
│       └── rules.py        # ERROR_RULES
├── tests/                  # stdlib unittest suite (69 tests)
├── logs/                   # auto-created at startup (cwd-based; override with LOGWISE_LOG_DIR)
├── dist/                   # uv build output (git-ignored)
└── .venv/                  # uv venv (git-ignored)
```

## Development

```bash
uv sync --group dev        # install dev tools (ruff)
uv run python -m unittest discover   # 69 tests, stdlib only
uv run --group dev ruff check src tests
uv run --group dev ruff format --check src tests
uv run logwise run "ls /missing/path"   # rules path
uv run logwise run "echo hi"            # success path
uv run logwise list
uv run logwise prune --keep 50 --yes    # rotate old logs
uv build                 # wheel + sdist into dist/
```

CI (`.github/workflows/ci.yml`) runs ruff, the test suite, and `uv build` on every push to `main` and every PR. To exercise the AI layer without spending API calls, point `LOGWISE_BASE_URL` at any stub that answers `POST /chat/completions` with `{"choices": [{"message": {"content": "..."}}]}`.

## Publishing to PyPI

The package is publish-ready: SPDX license, readme, classifiers, project URLs, `src` layout, and two runtime dependencies (`typer`, `rich`).

```bash
uv build               # wheel + sdist into dist/
uv publish             # needs a PyPI token (or: twine upload dist/*)
```

Checklist before the first upload:

1. `uv build` succeeds with no warnings.
2. Bump `version` in `pyproject.toml` for every subsequent release.
3. Never commit `.env` (git-ignored) or `dist/` (git-ignored).
4. `pip install logwise` in a fresh venv, then `logwise run "ls /missing"` from an unrelated directory — logs must land in that directory's `logs/`, never in `site-packages`.

## Contributing

Contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes (new rules go in `rules.py`, new vendors in `providers.py`)
4. Sanity-check with `uv run logwise run` on a failing + passing command
5. Submit a pull request

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Maintainer

Dhanush Ballanki
