from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class SandboxError(ValueError):
    """Raised when a requested path or command violates sandbox policy."""


@dataclass(frozen=True)
class Sandbox:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.resolve())

    def resolve_path(self, path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise SandboxError(f"Path escapes workspace: {path}") from exc
        return resolved


_DANGEROUS_PATTERNS = [
    r"\brm\s+.*-[^\n]*r",
    r"\bdel\s+.*(/s|/q)",
    r"\brmdir\s+.*(/s|/q)",
    r"\bformat\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[^\n]*f",
    r"\bRemove-Item\b.*-Recurse\b",
    r"\brd\s+.*(/s|/q)",
]


def assert_command_safe(command: str) -> None:
    normalized = command.strip()
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            raise SandboxError(f"Command blocked by safety policy: {command}")


