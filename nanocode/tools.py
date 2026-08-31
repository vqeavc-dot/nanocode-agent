from __future__ import annotations

import ast
import json
import py_compile
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .repo_map import DEFAULT_IGNORE_DIRS, RepoMap
from .sandbox import Sandbox, SandboxError, assert_command_safe


MAX_OUTPUT_CHARS = 6000
MAX_SEARCH_FILE_BYTES = 200_000
MAX_MATCHES_PER_FILE = 5
HUNK_HEADER_RE = re.compile(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


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


@dataclass
class SearchMatch:
    path: str
    line_no: int
    line: str
    score: int

    def render(self) -> str:
        return f"{self.path}:{self.line_no}: {self.line.strip()[:160]}"


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
            _schema("list_files", "List files and directories in a workspace path.", {"path": "string", "limit": "integer"}),
            _schema("search_code", "Search text in workspace files and return ranked concise matches.", {"query": "string", "path": "string", "limit": "integer"}, ["query"]),
            _schema("list_symbols", "List Python classes and functions with line numbers for code-structure analysis.", {"path": "string", "limit": "integer"}),
            _schema("repo_map", "Build a compact repository map with imports, symbols, references, and dependency scores.", {"path": "string", "max_files": "integer", "max_chars": "integer"}),
            _schema("view_file", "View a numbered line window from a file.", {"path": "string", "start_line": "integer", "limit": "integer"}, ["path"]),
            _schema("edit_file", "Replace exactly one old_text occurrence in a file.", {"path": "string", "old_text": "string", "new_text": "string"}, ["path", "old_text", "new_text"]),
            _schema("write_file", "Create or overwrite a workspace file.", {"path": "string", "content": "string"}, ["path", "content"]),
            _schema("apply_patch_file", "Apply a single-file unified diff patch with context validation and rollback.", {"path": "string", "patch": "string"}, ["path", "patch"]),
            _schema("run_command", "Run a safe shell command in the workspace.", {"command": "string", "timeout": "integer"}, ["command"]),
            _schema("final_answer", "Finish the task with a concise summary.", {"summary": "string"}, ["summary"]),
        ]

    def run(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        table: dict[str, Callable[..., ToolResult]] = {
            "list_files": self.list_files,
            "search_code": self.search_code,
            "list_symbols": self.list_symbols,
            "repo_map": self.repo_map,
            "view_file": self.view_file,
            "edit_file": self.edit_file,
            "write_file": self.write_file,
            "apply_patch_file": self.apply_patch_file,
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

        matches = sorted(_collect_search_matches(root, self.workspace, query), key=lambda m: (-m.score, m.path, m.line_no))
        shown = matches[: max(1, limit)]
        if not shown:
            return ToolResult(True, "No matches")
        lines = [match.render() for match in shown]
        if len(matches) > len(shown):
            lines.append(f"... {len(matches) - len(shown)} more ranked matches not shown; narrow the search if needed")
        return ToolResult(True, "\n".join(lines), {"total_matches": len(matches)})

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

    def apply_patch_file(self, path: str, patch: str) -> ToolResult:
        target = self.sandbox.resolve_path(path)
        if not target.exists():
            return ToolResult(False, f"File does not exist: {path}")
        if not target.is_file():
            return ToolResult(False, f"Path is not a file: {path}")

        original = target.read_text(encoding="utf-8")
        try:
            updated = _apply_unified_patch(original, patch)
        except ToolExecutionError as exc:
            return ToolResult(False, str(exc))
        if updated == original:
            return ToolResult(False, "Patch made no changes")

        try:
            self._write_checked(target, updated)
        except ToolExecutionError as exc:
            return ToolResult(False, str(exc))
        return ToolResult(True, f"Applied patch to {Path(path).as_posix()}\n\n{self.view_file(path, 1, 80).content}")

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
        return bool(parts & DEFAULT_IGNORE_DIRS)


def _schema(name: str, description: str, properties: dict[str, str], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {key: {"type": value} for key, value in properties.items()},
                "required": required or [],
            },
        },
    }


def _collect_search_matches(root: Path, workspace: Path, query: str) -> list[SearchMatch]:
    lowered_query = query.lower()
    files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
    matches: list[SearchMatch] = []
    per_file_counts: dict[str, int] = {}
    for file_path in files:
        if _should_skip_path(file_path, workspace) or _too_large(file_path):
            continue
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        rel = file_path.relative_to(workspace).as_posix()
        for idx, line in enumerate(lines, start=1):
            if lowered_query not in line.lower():
                continue
            if per_file_counts.get(rel, 0) >= MAX_MATCHES_PER_FILE:
                continue
            per_file_counts[rel] = per_file_counts.get(rel, 0) + 1
            matches.append(SearchMatch(rel, idx, line, _score_search_match(rel, line, lowered_query)))
    return matches


def _score_search_match(path: str, line: str, lowered_query: str) -> int:
    lowered_path = path.lower()
    lowered_line = line.lower()
    score = 0
    if lowered_query in Path(path).name.lower():
        score += 60
    if re.search(r"\b(class|def|function|interface|enum)\b", lowered_line):
        score += 35
    if re.search(r"\b(import|from|require)\b", lowered_line):
        score += 15
    if "test" in lowered_path or "spec" in lowered_path:
        score += 10
    if "/src/" in f"/{lowered_path}" or lowered_path.startswith("src/"):
        score += 5
    score += max(0, 20 - len(line.strip()) // 20)
    return score


def _should_skip_path(path: Path, workspace: Path) -> bool:
    try:
        parts = set(path.relative_to(workspace).parts)
    except ValueError:
        return True
    return bool(parts & DEFAULT_IGNORE_DIRS)


def _too_large(path: Path) -> bool:
    try:
        return path.stat().st_size > MAX_SEARCH_FILE_BYTES
    except OSError:
        return True


def _confirm_with_stdin(command: str) -> bool:
    answer = input(f"Allow command? {command} [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... output truncated"


def _apply_unified_patch(original: str, patch: str) -> str:
    original_lines = original.splitlines(keepends=True)
    patch_lines = patch.splitlines(keepends=True)
    output: list[str] = []
    original_index = 0
    patch_index = 0
    saw_hunk = False

    while patch_index < len(patch_lines):
        line = patch_lines[patch_index]
        if line.startswith("--- ") or line.startswith("+++ "):
            patch_index += 1
            continue
        match = HUNK_HEADER_RE.match(line)
        if not match:
            patch_index += 1
            continue

        saw_hunk = True
        old_start = int(match.group(1))
        hunk_original_index = old_start - 1
        if hunk_original_index < original_index or hunk_original_index > len(original_lines):
            raise ToolExecutionError("Patch hunk line range is invalid")
        output.extend(original_lines[original_index:hunk_original_index])
        original_index = hunk_original_index
        patch_index += 1

        while patch_index < len(patch_lines):
            hunk_line = patch_lines[patch_index]
            if HUNK_HEADER_RE.match(hunk_line):
                break
            if hunk_line.startswith("\\ No newline at end of file"):
                patch_index += 1
                continue
            if not hunk_line:
                raise ToolExecutionError("Patch contains an empty hunk line without a prefix")
            prefix = hunk_line[0]
            content = hunk_line[1:]
            if prefix == " ":
                _require_original_line(original_lines, original_index, content)
                output.append(original_lines[original_index])
                original_index += 1
            elif prefix == "-":
                _require_original_line(original_lines, original_index, content)
                original_index += 1
            elif prefix == "+":
                output.append(content)
            else:
                raise ToolExecutionError(f"Unsupported patch line prefix: {prefix!r}")
            patch_index += 1

    if not saw_hunk:
        raise ToolExecutionError("Patch does not contain a unified diff hunk")
    output.extend(original_lines[original_index:])
    return "".join(output)


def _require_original_line(lines: list[str], index: int, expected: str) -> None:
    if index >= len(lines):
        raise ToolExecutionError("Patch context extends past end of file")
    actual = lines[index]
    if actual != expected:
        raise ToolExecutionError(
            "Patch context mismatch: "
            f"expected {expected.rstrip()!r}, found {actual.rstrip()!r}"
        )