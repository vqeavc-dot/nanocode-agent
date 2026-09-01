# NanoCode Agent Demo Script

## Command-line demo

1. Run `.\scripts\reset_demo.ps1`.
2. Run `.\scripts\run_demo.ps1`.
3. Point out the visible stages:
   - `[plan]`: lightweight planner.
   - `tool_call repo_map/search_code/view_file`: context selection.
   - `tool_call apply_patch_file/edit_file`: local edit action.
   - `tool_call run_command`: verifier.
   - `[verify]`: test signal detection.
   - `Git diff summary` and `Token usage`: observability.

## UI demo

1. Run `nanocode-ui`.
2. Open `http://127.0.0.1:8765`.
3. Use the "Verify calculator" or "Patch example" preset.
4. Explain that the UI is only a presentation layer; the handwritten local agent loop executes underneath.

## Oral explanation

NanoCode uses ReAct as the core because coding tasks need repeated observation and adjustment. A lightweight local planner provides an initial route, while the skill-like tool registry exposes repository map, search, file viewing, patch editing, command execution, and final answer tools. This keeps the project explainable without depending on forbidden agent frameworks.
