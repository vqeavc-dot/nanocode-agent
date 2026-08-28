from __future__ import annotations

import argparse
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
    log_path = None if args.no_log else _write_run_log(args.log_dir, args.task, result, diff_summary)
    print(result.final)
    if result.usage:
        print(format_usage(result.usage))
    if diff_summary:
        print(diff_summary)
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


def format_usage(usage: dict[str, int]) -> str:
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    total = usage.get("total_tokens", prompt + completion)
    return f"Token usage: prompt={prompt}, completion={completion}, total={total}"


def _write_run_log(log_dir: str, task: str, result: AgentResult, diff_summary: str) -> Path:
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
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


if __name__ == "__main__":
    raise SystemExit(main())
