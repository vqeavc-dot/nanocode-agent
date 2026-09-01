# NanoCode Agent

NanoCode Agent is a small coding agent implemented without agent frameworks. Its architecture is **ReAct + Lightweight Planner + Skill-like Tools**: a short local plan starts the run, then a hand-written model-tool-observation loop uses local repository tools to inspect, edit, verify, and summarize code changes.

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

Each run writes a Markdown trace to `run_logs/` by default. Use `--no-log` to disable log files. Add `--auto-commit` only when you want NanoCode to commit changes after it observes a successful test command. Run tests:

```powershell
pytest
```


## Web UI

NanoCode also includes a small local web UI for demonstrations:

```powershell
nanocode-ui
```

Open `http://127.0.0.1:8765` to submit a task and inspect the step timeline, tool calls, observations, token usage, run log path, and git diff summary. The UI is only a presentation layer; the same local agent loop and tools do the work.

## Demo Scripts

```powershell
.\scripts\reset_demo.ps1
.\scripts\run_demo.ps1
```

`run_demo.ps1` runs a reproducible calculator task with verbose tracing. Use it as the command-line path for the final video, or run `nanocode-ui` for the visual path.

After recording the final MP4, create the required submission zip:

```powershell
.\scripts\package_submission.ps1 -Name "你的姓名" -VideoPath ".\demo.mp4"
```

## Core Design

- Agent Loop: the ReAct loop calls the model, parses tool calls, executes local tools, records observations, and stops on `final_answer` or a step limit.
- Lightweight Planner: a deterministic planner writes an initial plan into the prompt, transcript, run log, and UI before the ReAct loop starts.
- Memory: recent observations stay intact while older observations are compressed into summaries.
- Tool Registry: skill-like tools are described in a catalog and exposed as OpenAI-compatible tool schemas.
- RepoMap: compact repository summaries include symbols, imports, references, def/ref dependencies, and lightweight PageRank-style scores.
- Patch Editor: `apply_patch_file` applies single-file unified diffs with context validation and Python rollback checks.
- Sandbox: file access is limited to the workspace and risky shell commands are blocked.
- Verifier: `run_command` observations are inspected for test signals; `--auto-commit` is allowed only after successful tests are observed.
- Logger/UI: CLI and web UI show plan, steps, tool calls, observations, verification signals, token usage, run logs, and git diff summaries.

## Tool Catalog

| Stage | Tools |
| --- | --- |
| Context | `repo_map`, `search_code`, `list_files`, `list_symbols`, `view_file` |
| Edit | `apply_patch_file`, `edit_file`, `write_file` |
| Verify | `run_command` |
| Finish | `final_answer` |

## Safety

NanoCode restricts file access to the configured workspace, blocks risky shell commands, optionally asks for confirmation before shell execution, truncates long outputs, limits the number of agent steps, and runs Python syntax checks after editing `.py` files. NanoCode retries transient model API failures, reports token usage when the provider returns it, and prints a git diff summary after each run.
