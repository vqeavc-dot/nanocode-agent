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
nanocode "Add divide() to examples/calculator and run tests"
```

Run tests:

```powershell
pytest
```

## Core Design

- Planning: the model decides the next tool call after each observation.
- Memory: the agent keeps recent observations intact and summarizes older ones.
- Perception: tools expose repository state through concise search results, file windows, and command output.
- Action: local tools read, write, edit, and execute commands inside a sandboxed workspace.

## Safety

NanoCode restricts file access to the configured workspace, blocks risky shell commands, truncates long outputs, limits the number of agent steps, and runs Python syntax checks after editing `.py` files.

