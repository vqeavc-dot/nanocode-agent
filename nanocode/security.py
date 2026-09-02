from __future__ import annotations

import re
from pathlib import Path


PROTECTED_FILENAMES = {".env", ".env.local", ".env.production", ".env.development"}
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,}|(?:[A-Z0-9_]*(?:API|TOKEN|SECRET|KEY)[A-Z0-9_]*\s*=\s*['\"]?(?:sk-[A-Za-z0-9_-]{8,}|[A-Za-z0-9_-]{24,})['\"]?)|authorization:\s*bearer\s+[A-Za-z0-9_.-]{8,})",
    re.IGNORECASE,
)


def is_protected_path(path: Path) -> bool:
    name = path.name.lower()
    return name in PROTECTED_FILENAMES


def redact_secrets(text: str) -> str:
    return SECRET_RE.sub(_redact_match, text)


def _redact_match(match: re.Match[str]) -> str:
    value = match.group(0)
    if "=" in value:
        key = value.split("=", 1)[0].strip()
        return f"{key}=[REDACTED]"
    if value.lower().startswith("authorization:"):
        return "Authorization: Bearer [REDACTED]"
    return "[REDACTED_SECRET]"
