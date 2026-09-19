# LogWise

LogWise is a lightweight Python CLI for capturing command output, detecting common failure patterns, and suggesting fixes for failed shell commands. It stores failed executions as JSON logs, analyzes them with built-in rules, and can optionally use Google Gemini for AI-enhanced troubleshooting.

## Why LogWise?

When a command fails, the usual workflow is: rerun it, inspect the output, and try to infer the root cause. LogWise speeds that up by:

- running commands through a simple CLI,
- capturing stdout, stderr, exit codes, and timestamps,
- logging failures for later inspection,
- detecting common issues such as permission errors and missing files,
- suggesting practical fixes immediately,
- optionally using AI to explain the problem in plain language.

## Features

- Command execution with automatic error detection
- Captured logs stored in JSON format under the `logs/` directory
- Rule-based issue detection for common shell problems
- AI-assisted diagnosis using Gemini when enabled
- CLI commands for running, analyzing, and listing logs
- Easy Python installation via pip / editable install

## Requirements

- Python 3.10+
- A terminal environment
- Optional: `GEMINI_API_KEY` for AI-powered analysis

## Installation

Clone the repository:

```bash
git clone https://github.com/dhanush-ballanki/logwise.git
cd logwise
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate   # Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
pip install -e .
```

If you want to enable AI analysis, set your Gemini API key:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

## Usage

### Run a command

```bash
logwise run "python script.py"
```

This executes the command and prints its output if it succeeds. If it fails, LogWise captures the error and analyzes it.

To use AI-enhanced analysis:

```bash
logwise run "python script.py" --ai
```

### Analyze an existing log

```bash
logwise analyze log_2025-04-06T10-30-00.json
```

With AI analysis enabled:

```bash
logwise analyze log_2025-04-06T10-30-00.json --ai
```

### List captured logs

```bash
logwise list
```

## Example

```bash
logwise run "ls /missing/path"
```

Example result:

```text
Error occurred (exit code: 2)
Stderr captured:
ls: cannot access '/missing/path': No such file or directory

Analysis:
Found 1 rule-based issue(s).
- Reason: File or directory not found. (Path issue.)
  Steps to fix: Check if the file exists (ls), correct the path, or create the missing item.
```

## Rule-based detection

LogWise currently checks for common error categories, including:

- non-zero exit codes
- permission denied errors
- file not found / no such file or directory errors

These checks are configured in `src/logwise/rules.py` and can be extended as needed.

## AI analysis

When `--ai` is used, LogWise calls the Google Gemini API to provide:

- a concise explanation of the error,
- step-by-step remediation guidance,
- fallback reasoning when no rule matches.

AI analysis is only attempted if `GEMINI_API_KEY` is set.

## Project structure

```text
logwise/
├── LICENSE
├── README.md
├── pyproject.toml
├── requirements.txt
├── src/
│   └── logwise/
│       ├── ai.py
│       ├── analyze.py
│       ├── capture.py
│       ├── main.py
│       └── rules.py
├── logs/                # created automatically when commands fail
└── .gitignore
```

## Contributing

Contributions are welcome. If you want to improve the tool:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests or sanity checks
5. Submit a pull request

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Maintainer

Dhanush Ballanki
