from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from .security import is_protected_path


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
TOKEN_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


@dataclass
class FileSummary:
    path: str
    imports: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    definitions: set[str] = field(default_factory=set)
    references: set[str] = field(default_factory=set)
    dependencies: list[str] = field(default_factory=list)
    score: float = 0.0
    skipped_reason: str | None = None

    def render(self) -> list[str]:
        if self.skipped_reason:
            return [f"{self.path}", f"  skipped: {self.skipped_reason}"]
        lines = [f"{self.path}  score={self.score:.3f}"]
        if self.dependencies:
            lines.append("  depends_on: " + ", ".join(self.dependencies[:8]))
        if self.imports:
            lines.append("  imports: " + ", ".join(self.imports[:12]))
        if self.symbols:
            lines.extend(f"  {symbol}" for symbol in self.symbols[:24])
        if self.references:
            refs = sorted(self.references - self.definitions)[:12]
            if refs:
                lines.append("  refs: " + ", ".join(refs))
        if not self.imports and not self.symbols and not self.references:
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
        root = self.root.resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Path escapes workspace: {path}") from exc
        if not target.exists():
            return f"Path does not exist: {path}"

        files = [target] if target.is_file() else list(self._iter_source_files(target))
        summaries = [self._summarize_file(file_path) for file_path in files[: self.max_files]]
        _connect_and_rank(summaries)
        summaries = sorted(summaries, key=lambda item: (-item.score, item.path))
        lines = [
            f"Repo map for {Path(path).as_posix()}",
            f"files_shown={len(summaries)} files_total_at_least={len(files)} max_file_bytes={self.max_file_bytes}",
            "ranking=lightweight_def_ref_pagerank",
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
            if is_protected_path(path):
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
            imports, symbols, definitions, references = summarize_python_details(text)
        elif suffix in {".js", ".jsx", ".ts", ".tsx"}:
            imports, symbols, definitions, references = summarize_javascript_details(text)
        elif suffix == ".java":
            imports, symbols, definitions, references = summarize_java_details(text)
        else:
            imports, symbols, definitions, references = [], [], set(), set()
        return FileSummary(path=rel, imports=imports, symbols=symbols, definitions=definitions, references=references)

    def _is_ignored(self, path: Path) -> bool:
        rel_parts = path.relative_to(self.root.resolve()).parts
        return any(part in self.ignore_dirs for part in rel_parts)


def summarize_python(text: str) -> tuple[list[str], list[str]]:
    imports, symbols, _, _ = summarize_python_details(text)
    return imports, symbols


def summarize_python_details(text: str) -> tuple[list[str], list[str], set[str], set[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [], [f"parse_error line {exc.lineno}: {exc.msg}"], set(), set()

    imports: list[str] = []
    symbols: list[str] = []
    definitions: set[str] = set()
    references: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            references.add(node.id)
        elif isinstance(node, ast.Attribute):
            references.add(node.attr)
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
            references.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            imports.append(module)
            references.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ClassDef):
            definitions.add(node.name)
            symbols.append(f"line {node.lineno}: class {node.name}")
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(f"line {child.lineno}: method {node.name}.{child.name}")
        elif isinstance(node, ast.AsyncFunctionDef):
            definitions.add(node.name)
            symbols.append(f"line {node.lineno}: async def {node.name}")
        elif isinstance(node, ast.FunctionDef):
            definitions.add(node.name)
            symbols.append(f"line {node.lineno}: def {node.name}")
    return _dedupe(imports), symbols, definitions, references


_JS_IMPORT_RE = re.compile(r"^\s*(?:import\s+[^;]+\s+from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"]|const\s+\w+\s*=\s*require\(['\"]([^'\"]+)['\"]\))", re.MULTILINE)
_JS_SYMBOL_RE = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(|^\s*(?:export\s+)?class\s+(\w+)|^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(?[^=]*?=>", re.MULTILINE)


def summarize_javascript_like(text: str) -> tuple[list[str], list[str]]:
    imports, symbols, _, _ = summarize_javascript_details(text)
    return imports, symbols


def summarize_javascript_details(text: str) -> tuple[list[str], list[str], set[str], set[str]]:
    imports = [_first_group(match) for match in _JS_IMPORT_RE.finditer(text)]
    definitions: set[str] = set()
    symbols: list[str] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        match = _JS_SYMBOL_RE.match(line)
        if match:
            name = _first_group(match)
            definitions.add(name)
            kind = "class" if "class" in line else "function"
            symbols.append(f"line {idx}: {kind} {name}")
    references = set(TOKEN_RE.findall(text))
    return _dedupe(imports), symbols, definitions, references


_JAVA_IMPORT_RE = re.compile(r"^\s*import\s+([\w.*]+);", re.MULTILINE)
_JAVA_TYPE_RE = re.compile(r"^\s*(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?(?:class|interface|enum)\s+(\w+)", re.MULTILINE)
_JAVA_METHOD_RE = re.compile(r"^\s*(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?[\w<>\[\], ?]+\s+(\w+)\s*\([^;]*\)\s*\{", re.MULTILINE)


def summarize_java(text: str) -> tuple[list[str], list[str]]:
    imports, symbols, _, _ = summarize_java_details(text)
    return imports, symbols


def summarize_java_details(text: str) -> tuple[list[str], list[str], set[str], set[str]]:
    imports = _JAVA_IMPORT_RE.findall(text)
    definitions: set[str] = set()
    symbols: list[str] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        type_match = _JAVA_TYPE_RE.match(line)
        if type_match:
            name = type_match.group(1)
            definitions.add(name)
            symbols.append(f"line {idx}: type {name}")
            continue
        method_match = _JAVA_METHOD_RE.match(line)
        if method_match:
            name = method_match.group(1)
            definitions.add(name)
            symbols.append(f"line {idx}: method {name}")
    references = set(TOKEN_RE.findall(text))
    return _dedupe(imports), symbols, definitions, references


def _connect_and_rank(summaries: list[FileSummary]) -> None:
    active = [summary for summary in summaries if not summary.skipped_reason]
    definitions: dict[str, set[str]] = {}
    for summary in active:
        for name in summary.definitions:
            definitions.setdefault(name, set()).add(summary.path)

    edges: dict[str, set[str]] = {summary.path: set() for summary in active}
    for summary in active:
        for ref in summary.references:
            for target in definitions.get(ref, set()):
                if target != summary.path:
                    edges[summary.path].add(target)
        summary.dependencies = sorted(edges[summary.path])

    scores = _pagerank(edges)
    for summary in summaries:
        summary.score = scores.get(summary.path, 0.0)


def _pagerank(edges: dict[str, set[str]], rounds: int = 20, damping: float = 0.85) -> dict[str, float]:
    if not edges:
        return {}
    nodes = list(edges)
    n = len(nodes)
    scores = {node: 1.0 / n for node in nodes}
    for _ in range(rounds):
        next_scores = {node: (1.0 - damping) / n for node in nodes}
        for source, targets in edges.items():
            if not targets:
                share = scores[source] / n
                for node in nodes:
                    next_scores[node] += damping * share
                continue
            share = scores[source] / len(targets)
            for target in targets:
                next_scores[target] += damping * share
        scores = next_scores
    return scores


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
