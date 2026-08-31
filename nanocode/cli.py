from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .agent import AgentResult, CodingAgent
from .config import load_config
from .llm import OpenAICompatibleLLM
from .tools import LocalTools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NanoCode Agent")
    parser.add_argument("task", help="Programming task for the agent")
    parser.add_argument("--workspace", default=".", help="Workspace directory")
    parser.add_argument("--max-steps", type=int, default=None, help="Maximum agent steps")
    parser.add_argument("--verbose", action="store_true", help="Print every agent step and tool observation")
    parser.add_argument("--log-dir", default="run_logs", help="Directory for Markdown run logs")
    parser.add_argument("--no-log", action="store_true", help="Disable writing a run log")
    parser.add_argument("--confirm-actions", action="store_true", help="Ask before executing shell commands")
    parser.add_argument("--no-diff-summary", action="store_true", help="Do not print git diff summary after a run")
    parser.add_argument("--auto-commit", action="store_true", help="Commit workspace changes after a successful, tested run")
    parser.add_argument("--commit-message", default=None, help="Commit message used with --auto-commit")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()
    if not config.api_key:
        print("NANOCODE_API_KEY is not set. Copy .env.example to .env and fill it.", file=sys.stderr)
        return 2

    workspace = config.workspace if args.workspace == "." else (config.workspace / args.workspace).resolve()
    tools = LocalTools(workspace, confirm_commands=args.confirm_actions)
    model = OpenAICompatibleLLM(config.api_key, config.base_url, config.model)
    agent = CodingAgent(
        model=model,
        tools=tools,
        max_steps=args.max_steps or config.max_steps,
        verbose=args.verbose,
    )
    result = agent.run(args.task)
    diff_summary = "" if args.no_diff_summary else collect_git_diff_summary(workspace)
    commit_summary = ""
    if args.auto_commit:
        commit_summary = auto_commit_changes(workspace, result, args.commit_message)
        if not args.no_diff_summary:
            diff_summary = collect_git_diff_summary(workspace)
    log_path = None if args.no_log else _write_run_log(args.log_dir, args.task, result, diff_summary, commit_summary)
    print(result.final)
    if result.usage:
        print(format_usage(result.usage))
    if diff_summary:
        print(diff_summary)
    if commit_summary:
        print(commit_summary)
    if log_path is not None:
        print(f"Run log: {log_path}")
    return 1 if result.stopped_by_limit else 0


def collect_git_diff_summary(workspace: Path) -> str:
    if not (workspace / ".git").exists():
        return ""
    try:
        stat = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=10,
        )
        names = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if stat.returncode != 0 or names.returncode != 0 or not stat.stdout.strip():
        return ""
    changed = ", ".join(line.strip() for line in names.stdout.splitlines() if line.strip())
    return f"Git diff summary:\n{stat.stdout.strip()}\nChanged files: {changed}"


def auto_commit_changes(workspace: Path, result: AgentResult, message: str | None = None) -> str:
    if result.stopped_by_limit:
        return "Auto commit skipped: agent stopped by step limit."
    if not _run_looked_tested(result):
        return "Auto commit skipped: no successful test command was observed."
    if not (workspace / ".git").exists():
        return "Auto commit skipped: workspace is not a Git repository."
    if not _has_worktree_changes(workspace):
        return "Auto commit skipped: no workspace changes to commit."

    commit_message = _sanitize_commit_message(message or _default_commit_message(result.final))
    add = subprocess.run(["git", "add", "-A"], cwd=workspace, text=True, capture_output=True, timeout=20)
    if add.returncode != 0:
        return f"Auto commit failed during git add: {add.stderr.strip()}"
    commit = subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=workspace,
        text=True,
        capture_output=True,
        timeout=20,
    )
    if commit.returncode != 0:
        return f"Auto commit failed during git commit: {(commit.stderr or commit.stdout).strip()}"
    first_line = commit.stdout.splitlines()[0] if commit.stdout.splitlines() else commit_message
    return f"Auto commit created: {first_line}"


def format_usage(usage: dict[str, int]) -> str:
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    total = usage.get("total_tokens", prompt + completion)
    return f"Token usage: prompt={prompt}, completion={completion}, total={total}"


def _write_run_log(log_dir: str, task: str, result: AgentResult, diff_summary: str, commit_summary: str = "") -> Path:
    target_dir = Path(log_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = target_dir / f"run-{timestamp}.md"
    lines = [
        "# NanoCode Run Log",
        "",
        f"Time: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Task",
        "",
        task,
        "",
        "## Transcript",
        "",
    ]
    lines.extend(f"- {event}" for event in result.transcript)
    lines.extend(["", "## Final", "", result.final, ""])
    if result.usage:
        lines.extend(["## Usage", "", format_usage(result.usage), ""])
    if diff_summary:
        lines.extend(["## Git Diff Summary", "", diff_summary, ""])
    if commit_summary:
        lines.extend(["## Auto Commit", "", commit_summary, ""])
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def _run_looked_tested(result: AgentResult) -> bool:
    for event in result.transcript:
        lowered = event.lower()
        if "observation run_command ok=true" in lowered and any(word in lowered for word in ["pytest", "passed", "test"]):
            return True
    return False


def _has_worktree_changes(workspace: Path) -> bool:
    status = subprocess.run(["git", "status", "--short"], cwd=workspace, text=True, capture_output=True, timeout=10)
    return status.returncode == 0 and bool(status.stdout.strip())


def _default_commit_message(final: str) -> str:
    first = final.strip().splitlines()[0] if final.strip() else "Apply NanoCode agent changes"
    return first[:72] or "Apply NanoCode agent changes"


def _sanitize_commit_message(message: str) -> str:
    cleaned = re.sub(r"\s+", " ", message).strip()
    return cleaned[:120] or "Apply NanoCode agent changes"


if __name__ == "__main__":
    raise SystemExit(main())
