from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_IGNORE_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "run_logs",
    "venv",
}
SUPPORTED_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".java"}


@dataclass
class FileSummary:
    path: str
    imports: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    skipped_reason: str | None = None

    def render(self) -> list[str]:
        if self.skipped_reason:
            return [f"{self.path}", f"  skipped: {self.skipped_reason}"]
        lines = [self.path]
        if self.imports:
            lines.append("  imports: " + ", ".join(self.imports[:12]))
        if self.symbols:
            lines.extend(f"  {symbol}" for symbol in self.symbols[:24])
        if not self.imports and not self.symbols:
            lines.append("  no top-level symbols found")
        return lines


@dataclass
class RepoMap:
    root: Path
    max_files: int = 80
    max_file_bytes: int = 200_000
    max_chars: int = 10_000
    ignore_dirs: set[str] = field(default_factory=lambda: set(DEFAULT_IGNORE_DIRS))

    def build(self, path: str | Path = ".") -> str:
        target = (self.root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        try:
            target.relative_to(self.root.resolve())
        except ValueError as exc:
            raise ValueError(f"Path escapes workspace: {path}") from exc
        if not target.exists():
            return f"Path does not exist: {path}"

        files = [target] if target.is_file() else list(self._iter_source_files(target))
        summaries = [self._summarize_file(file_path) for file_path in files[: self.max_files]]
        lines = [
            f"Repo map for {Path(path).as_posix()}",
            f"files_shown={len(summaries)} files_total_at_least={len(files)} max_file_bytes={self.max_file_bytes}",
            "",
        ]
        for summary in summaries:
            lines.extend(summary.render())
            lines.append("")
        if len(files) > len(summaries):
            lines.append(f"... {len(files) - len(summaries)} more source files not shown")
        rendered = "\n".join(lines).strip()
        if len(rendered) > self.max_chars:
            return rendered[: self.max_chars - 28].rstrip() + "\n... repo map truncated"
        return rendered

    def _iter_source_files(self, root: Path):
        for path in sorted(root.rglob("*"), key=lambda p: p.as_posix().lower()):
            if not path.is_file():
                continue
            if self._is_ignored(path):
                continue
            if path.suffix.lower() in SUPPORTED_SUFFIXES:
                yield path

    def _summarize_file(self, path: Path) -> FileSummary:
        rel = path.relative_to(self.root.resolve()).as_posix()
        try:
            size = path.stat().st_size
        except OSError as exc:
            return FileSummary(path=rel, skipped_reason=f"stat failed: {exc}")
        if size > self.max_file_bytes:
            return FileSummary(path=rel, skipped_reason=f"file too large ({size} bytes)")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return FileSummary(path=rel, skipped_reason="not utf-8 text")

        suffix = path.suffix.lower()
        if suffix == ".py":
            imports, symbols = summarize_python(text)
        elif suffix in {".js", ".jsx", ".ts", ".tsx"}:
            imports, symbols = summarize_javascript_like(text)
        elif suffix == ".java":
            imports, symbols = summarize_java(text)
        else:
            imports, symbols = [], []
        return FileSummary(path=rel, imports=imports, symbols=symbols)

    def _is_ignored(self, path: Path) -> bool:
        rel_parts = path.relative_to(self.root.resolve()).parts
        return any(part in self.ignore_dirs for part in rel_parts)


def summarize_python(text: str) -> tuple[list[str], list[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [], [f"parse_error line {exc.lineno}: {exc.msg}"]

    imports: list[str] = []
    symbols: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            imports.append(module)
        elif isinstance(node, ast.ClassDef):
            symbols.append(f"line {node.lineno}: class {node.name}")
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(f"line {child.lineno}: method {node.name}.{child.name}")
        elif isinstance(node, ast.AsyncFunctionDef):
            symbols.append(f"line {node.lineno}: async def {node.name}")
        elif isinstance(node, ast.FunctionDef):
            symbols.append(f"line {node.lineno}: def {node.name}")
    return _dedupe(imports), symbols


_JS_IMPORT_RE = re.compile(r"^\s*(?:import\s+[^;]+\s+from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"]|const\s+\w+\s*=\s*require\(['\"]([^'\"]+)['\"]\))", re.MULTILINE)
_JS_SYMBOL_RE = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(|^\s*(?:export\s+)?class\s+(\w+)|^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(?[^=]*?=>", re.MULTILINE)


def summarize_javascript_like(text: str) -> tuple[list[str], list[str]]:
    imports = [_first_group(match) for match in _JS_IMPORT_RE.finditer(text)]
    symbols: list[str] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        match = _JS_SYMBOL_RE.match(line)
        if match:
            name = _first_group(match)
            kind = "class" if "class" in line else "function"
            symbols.append(f"line {idx}: {kind} {name}")
    return _dedupe(imports), symbols


_JAVA_IMPORT_RE = re.compile(r"^\s*import\s+([\w.*]+);", re.MULTILINE)
_JAVA_TYPE_RE = re.compile(r"^\s*(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?(?:class|interface|enum)\s+(\w+)", re.MULTILINE)
_JAVA_METHOD_RE = re.compile(r"^\s*(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?[\w<>\[\], ?]+\s+(\w+)\s*\([^;]*\)\s*\{", re.MULTILINE)


def summarize_java(text: str) -> tuple[list[str], list[str]]:
    imports = _JAVA_IMPORT_RE.findall(text)
    symbols: list[str] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        type_match = _JAVA_TYPE_RE.match(line)
        if type_match:
            symbols.append(f"line {idx}: type {type_match.group(1)}")
            continue
        method_match = _JAVA_METHOD_RE.match(line)
        if method_match:
            symbols.append(f"line {idx}: method {method_match.group(1)}")
    return _dedupe(imports), symbols


def _first_group(match: re.Match[str]) -> str:
    for group in match.groups():
        if group:
            return group
    return "unknown"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
