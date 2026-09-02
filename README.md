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
nanocode "Add divide() to examples/calculator and run tests" --verbose --mode trust
```

NanoCode defaults to `--mode review`, which favors inspection and command confirmation. Use `--mode trust` for demos or familiar workspaces where safe commands may run without extra confirmation. Each run writes a Markdown trace to `run_logs/` by default. Use `--no-log` to disable log files. Add `--auto-commit` only in trust mode when you want NanoCode to commit changes after it observes a successful test command. Run tests:

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
- Review/Trust Modes: review mode is conservative by default; trust mode must be explicitly selected before automatic commits are allowed.
- Task Profile: `TaskClassifier` labels the request as explanation, bug fix, feature, test, review, or refactor and assigns a risk level.
- Skill Registry: task profiles map to skill-like workflows such as code question, bug fix, feature change, test work, review, and safe refactor.
- Lightweight Planner: a deterministic planner selects a skill and writes an initial plan into the prompt, transcript, run log, and UI before the ReAct loop starts.
- Memory: recent observations stay intact while older observations are compressed into summaries; selected files, task profile, plan, and verification status are also tracked.
- Tool Registry: skill-like tools are described in a catalog and exposed as OpenAI-compatible tool schemas.
- RepoMap: compact repository summaries include symbols, imports, references, def/ref dependencies, and lightweight PageRank-style scores.
- Patch Editor: `apply_patch_file` applies single-file unified diffs with context validation and Python rollback checks.
- Safety Rails: file access is limited to the workspace, risky shell commands are blocked, tools carry risk levels, and secret scans avoid printing secret values.
- Verifier/Reflection: test observations are inspected for success signals; failed tools are classified by `FailureAnalyzer` to guide the next ReAct step.
- Logger/UI: CLI and web UI show mode, task profile, skill, plan, steps, tool calls, observations, reflection, verification, token usage, run logs, and git diff summaries.

## Tool Catalog

| Stage | Tools |
| --- | --- |
| Context | `repo_map`, `search_code`, `list_files`, `list_symbols`, `view_file`, `inspect_git_status` |
| Edit | `apply_patch_file`, `edit_file`, `write_file` |
| Verify | `run_tests`, `run_command` |
| Safety | `secret_scan` |
| Finish | `final_answer` |

## Design Route

The project follows a seven-step landing route rather than starting from a framework: job description, minimal toolbox, skill-like workflows, planning/reflection, memory, safety rails, and evaluation. See `docs/agent_design.md` for the full design rationale.

## Evaluation

`evals/coding_agent_cases.json` contains scenario and red-team cases. They describe expected tool traces and safety expectations such as blocking workspace escape and destructive commands. This complements unit tests by making the agent's behavior auditable.

## Review and Trust

Review mode is for learning, demos with careful explanation, and unfamiliar repositories. It highlights the plan, observations, verification, and diff before the user trusts the result. Trust mode is for controlled workspaces: safe commands can run without an extra prompt, and `--auto-commit` may create a commit after tests pass.

## Safety

NanoCode restricts file access to the configured workspace, blocks risky shell commands, optionally asks for confirmation before shell execution, truncates long outputs, limits the number of agent steps, and runs Python syntax checks after editing `.py` files. NanoCode retries transient model API failures, reports token usage when the provider returns it, and prints a git diff summary after each run.
