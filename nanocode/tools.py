from __future__ import annotations

import ast
import json
import py_compile
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .repo_map import RepoMap
from .sandbox import Sandbox, SandboxError, assert_command_safe


MAX_OUTPUT_CHARS = 6000


class ToolExecutionError(RuntimeError):
    """Raised when a tool action is valid but cannot be completed."""


@dataclass
class ToolResult:
    ok: bool
    content: str
    data: dict[str, Any] | None = None

    def to_json(self) -> str:
        return json.dumps(
            {"ok": self.ok, "content": self.content, "data": self.data or {}},
            ensure_ascii=False,
        )


class LocalTools:
    def __init__(
        self,
        workspace: Path,
        confirm_commands: bool = False,
        confirmer: Callable[[str], bool] | None = None,
    ):
        self.workspace = workspace.resolve()
        self.sandbox = Sandbox(self.workspace)
        self.confirm_commands = confirm_commands
        self.confirmer = confirmer or _confirm_with_stdin

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files and directories in a workspace path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "."},
                            "limit": {"type": "integer", "default": 80},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_code",
                    "description": "Search text in workspace files and return concise matches.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "path": {"type": "string", "default": "."},
                            "limit": {"type": "integer", "default": 30},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_symbols",
                    "description": "List Python classes and functions with line numbers for code-structure analysis.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "."},
                            "limit": {"type": "integer", "default": 80},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "repo_map",
                    "description": "Build a compact repository map with files, imports, classes, and functions before opening specific files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "."},
                            "max_files": {"type": "integer", "default": 80},
                            "max_chars": {"type": "integer", "default": 10000},
                        },
                    },
                },
            },            {
                "type": "function",
                "function": {
                    "name": "view_file",
                    "description": "View a numbered line window from a file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "start_line": {"type": "integer", "default": 1},
                            "limit": {"type": "integer", "default": 100},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Replace exactly one old_text occurrence in a file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "old_text": {"type": "string"},
                            "new_text": {"type": "string"},
                        },
                        "required": ["path", "old_text", "new_text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Create or overwrite a workspace file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Run a safe shell command in the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "timeout": {"type": "integer", "default": 20},
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "final_answer",
                    "description": "Finish the task with a concise summary.",
                    "parameters": {
                        "type": "object",
                        "properties": {"summary": {"type": "string"}},
                        "required": ["summary"],
                    },
                },
            },
        ]

    def run(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        table: dict[str, Callable[..., ToolResult]] = {
            "list_files": self.list_files,
            "search_code": self.search_code,
            "list_symbols": self.list_symbols,
            "view_file": self.view_file,
            "edit_file": self.edit_file,
            "write_file": self.write_file,
            "run_command": self.run_command,
            "final_answer": self.final_answer,
        }
        if name not in table:
            return ToolResult(False, f"Unknown tool: {name}")
        try:
            return table[name](**arguments)
        except TypeError as exc:
            return ToolResult(False, f"Invalid arguments for {name}: {exc}")
        except SandboxError as exc:
            return ToolResult(False, str(exc))
        except ToolExecutionError as exc:
            return ToolResult(False, str(exc))
        except Exception as exc:  # pragma: no cover - last-resort safety
            return ToolResult(False, f"{name} failed: {type(exc).__name__}: {exc}")

    def list_files(self, path: str = ".", limit: int = 80) -> ToolResult:
        target = self.sandbox.resolve_path(path)
        if not target.exists():
            return ToolResult(False, f"Path does not exist: {path}")
        if not target.is_dir():
            return ToolResult(False, f"Path is not a directory: {path}")

        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        shown = entries[: max(1, limit)]
        lines = []
        for item in shown:
            rel = item.relative_to(self.workspace)
            kind = "dir " if item.is_dir() else "file"
            lines.append(f"{kind} {rel.as_posix()}")
        hidden = max(0, len(entries) - len(shown))
        if hidden:
            lines.append(f"... {hidden} more entries not shown")
        return ToolResult(True, "\n".join(lines) or "(empty)")

    def search_code(self, query: str, path: str = ".", limit: int = 30) -> ToolResult:
        if not query:
            return ToolResult(False, "query must not be empty")
        root = self.sandbox.resolve_path(path)
        if not root.exists():
            return ToolResult(False, f"Path does not exist: {path}")

        matches: list[str] = []
        files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        for file_path in files:
            if self._should_skip(file_path):
                continue
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for idx, line in enumerate(lines, start=1):
                if query in line:
                    rel = file_path.relative_to(self.workspace).as_posix()
                    matches.append(f"{rel}:{idx}: {line.strip()[:160]}")
                    if len(matches) >= limit:
                        return ToolResult(
                            True,
                            "\n".join(matches)
                            + "\n... result limit reached; narrow the search if needed",
                        )
        return ToolResult(True, "\n".join(matches) if matches else "No matches")

    def list_symbols(self, path: str = ".", limit: int = 80) -> ToolResult:
        root = self.sandbox.resolve_path(path)
        if not root.exists():
            return ToolResult(False, f"Path does not exist: {path}")

        files = [root] if root.is_file() else [p for p in root.rglob("*.py") if p.is_file()]
        symbols: list[str] = []
        for file_path in files:
            if self._should_skip(file_path) or file_path.suffix != ".py":
                continue
            try:
                tree = ast.parse(file_path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError) as exc:
                rel = file_path.relative_to(self.workspace).as_posix()
                symbols.append(f"{rel}: parse_error: {exc}")
                continue
            rel = file_path.relative_to(self.workspace).as_posix()
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    symbols.append(f"{rel}:{node.lineno}: class {node.name}")
                elif isinstance(node, ast.AsyncFunctionDef):
                    symbols.append(f"{rel}:{node.lineno}: async def {node.name}")
                elif isinstance(node, ast.FunctionDef):
                    symbols.append(f"{rel}:{node.lineno}: def {node.name}")
                if len(symbols) >= limit:
                    return ToolResult(True, "\n".join(symbols) + "\n... symbol limit reached")
        return ToolResult(True, "\n".join(symbols) if symbols else "No Python symbols found")

    def repo_map(self, path: str = ".", max_files: int = 80, max_chars: int = 10000) -> ToolResult:
        repo_map = RepoMap(
            root=self.workspace,
            max_files=max(1, min(max_files, 200)),
            max_chars=max(1000, min(max_chars, 30000)),
        )
        try:
            content = repo_map.build(path)
        except ValueError as exc:
            return ToolResult(False, str(exc))
        return ToolResult(True, content)
    def view_file(self, path: str, start_line: int = 1, limit: int = 100) -> ToolResult:
        target = self.sandbox.resolve_path(path)
        if not target.exists():
            return ToolResult(False, f"File does not exist: {path}")
        if not target.is_file():
            return ToolResult(False, f"Path is not a file: {path}")

        lines = target.read_text(encoding="utf-8").splitlines()
        total = len(lines)
        start = max(1, start_line)
        count = min(max(1, limit), 100)
        end = min(total, start + count - 1)
        window = lines[start - 1 : end]
        numbered = [f"{line_no}: {line}" for line_no, line in enumerate(window, start=start)]
        header = f"[File: {Path(path).as_posix()} | lines {start}-{end} of {total}]"
        footer = f"[{start - 1} lines above, {max(0, total - end)} lines below]"
        return ToolResult(True, "\n".join([header, *numbered, footer]))

    def edit_file(self, path: str, old_text: str, new_text: str) -> ToolResult:
        target = self.sandbox.resolve_path(path)
        if not target.exists():
            return ToolResult(False, f"File does not exist: {path}")
        content = target.read_text(encoding="utf-8")
        count = content.count(old_text)
        if count == 0:
            return ToolResult(False, "old_text was not found")
        if count > 1:
            return ToolResult(False, f"old_text matched {count} times; make it unique")

        updated = content.replace(old_text, new_text, 1)
        try:
            self._write_checked(target, updated)
        except ToolExecutionError as exc:
            return ToolResult(False, str(exc))
        line = updated[: updated.find(new_text) if new_text else 0].count("\n") + 1
        return self.view_file(str(target.relative_to(self.workspace)), max(1, line - 5), 30)

    def write_file(self, path: str, content: str) -> ToolResult:
        target = self.sandbox.resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._write_checked(target, content)
        except ToolExecutionError as exc:
            return ToolResult(False, str(exc))
        return ToolResult(True, f"Wrote {len(content)} characters to {Path(path).as_posix()}")

    def run_command(self, command: str, timeout: int = 20) -> ToolResult:
        assert_command_safe(command)
        if self.confirm_commands and not self.confirmer(command):
            return ToolResult(False, f"Command rejected by user confirmation: {command}")
        bounded_timeout = min(max(1, timeout), 60)
        completed = subprocess.run(
            command,
            cwd=self.workspace,
            shell=True,
            text=True,
            capture_output=True,
            timeout=bounded_timeout,
        )
        stdout = _truncate(completed.stdout)
        stderr = _truncate(completed.stderr)
        content = (
            f"exit_code={completed.returncode}\n"
            f"stdout:\n{stdout or '(empty)'}\n"
            f"stderr:\n{stderr or '(empty)'}"
        )
        return ToolResult(completed.returncode == 0, content, {"exit_code": completed.returncode})

    def final_answer(self, summary: str) -> ToolResult:
        return ToolResult(True, summary, {"final": True})

    def _write_checked(self, target: Path, content: str) -> None:
        original = target.read_text(encoding="utf-8") if target.exists() else None
        target.write_text(content, encoding="utf-8")
        if target.suffix == ".py":
            try:
                py_compile.compile(str(target), doraise=True)
            except py_compile.PyCompileError:
                if original is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_text(original, encoding="utf-8")
                raise ToolExecutionError("Python syntax check failed; edit was rolled back")

    def _should_skip(self, path: Path) -> bool:
        parts = set(path.relative_to(self.workspace).parts)
        return bool(parts & {".git", ".venv", "__pycache__", ".pytest_cache"})


def _confirm_with_stdin(command: str) -> bool:
    answer = input(f"Allow command? {command} [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... output truncated"
