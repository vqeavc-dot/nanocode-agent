# NanoCode Agent 2-Minute Video Plan

## Goal

Show NanoCode completing one real programming task while explaining why it is a coding agent rather than a wrapper around a chat model.

## Recommended Demo Task

```powershell
.\scripts\reset_demo.ps1
.\scripts\run_demo.ps1
```

The task asks NanoCode to inspect `examples/calculator`, ensure `divide(a, b)` and pytest coverage exist, make the smallest safe edit if needed, run tests, and summarize the diff.

## Timeline

### 0:00-0:15 Opening

Say:

> This is NanoCode Agent, a local coding agent built without LangChain, AutoGen, Agents SDK, Code Interpreter, or Files API. Its architecture is ReAct plus a lightweight planner and skill-like local tools.

Show the repository and `.env.example`, briefly mention the real API key is only in local `.env`.

### 0:15-0:35 Run The Task

Run:

```powershell
.\scripts\run_demo.ps1
```

Point to `--verbose --mode trust`. Say:

> Trust mode is explicitly enabled for this controlled demo. Review mode is the safer default.

### 0:35-1:15 Explain The Trace

Highlight these lines in the terminal or UI:

- `[mode]`: permission policy.
- `[profile]`: task type and risk classification.
- `[skill]`: selected workflow.
- `[plan]`: initial plan.
- `tool_call repo_map/search_code/view_file`: context selection.
- `tool_call apply_patch_file/edit_file`: local code edit.
- `observation`: real tool result returned to the model.
- `[reflect]`: structured failure feedback if a tool fails.
- `[verify]`: test result signal.

Say:

> The model decides actions, but Python owns the local execution. Every file read, patch, command, and error is turned into an observation and fed back into the ReAct loop.

### 1:15-1:40 Show Result And Tests

Show final answer, token usage, git diff summary, and run log path. Then show:

```powershell
python -m pytest
```

Say:

> The project includes unit tests for agent loop, memory, tools, sandbox, repo map, planner, skill registry, verifier, risk policy, UI, and eval cases.

### 1:40-2:00 Close

Say:

> The main design choice is to start from the coding-agent job description: choose relevant context, safely edit local files, verify with tests, and make every step auditable. Multi-agent review or testing can be added later on top of this reliable single-agent loop.

End by showing GitHub commit history.
