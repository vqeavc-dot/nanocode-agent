# NanoCode Agent

NanoCode Agent is a small coding agent implemented without agent frameworks. It uses a hand-written loop, OpenAI-compatible chat APIs, and local tools for code search, windowed file viewing, file editing, and command execution.

## Why This Project Exists

This project follows the idea of an Agent-Computer Interface: an LLM should not operate a repository only through raw shell commands. Instead, it gets compact, predictable tools and concise observations that are easier to reason over.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

Edit `.env` and set your API key and model.

Run a task:

```powershell
nanocode "Add divide() to examples/calculator and run tests" --verbose
```

Each run writes a Markdown trace to `run_logs/` by default. Use `--no-log` to disable log files. Run tests:

```powershell
pytest
```


## Web UI

NanoCode also includes a small local web UI for demonstrations:

```powershell
nanocode-ui
```

Open `http://127.0.0.1:8765` to submit a task and inspect the step timeline, tool calls, observations, token usage, run log path, and git diff summary. The UI is only a presentation layer; the same local agent loop and tools do the work.
## Core Design

- Planning: the model decides the next tool call after each observation.
- Memory: the agent keeps recent observations intact and summarizes older ones.
- Perception: tools expose repository state through repo maps, concise search results, file windows, and command output.
- Action: local tools read, write, edit with exact replacement or single-file unified diffs, inspect Python symbols, and execute commands inside a sandboxed workspace.

## Safety

NanoCode restricts file access to the configured workspace, blocks risky shell commands, optionally asks for confirmation before shell execution, truncates long outputs, limits the number of agent steps, and runs Python syntax checks after editing `.py` files. It also includes a lightweight repo map inspired by aider: Python symbols are extracted with AST, JavaScript/TypeScript/Java symbols are extracted with small parsers, large files and dependency folders are skipped, and output is capped by a character budget. NanoCode retries transient model API failures, reports token usage when the provider returns it, and prints a git diff summary after each run.
