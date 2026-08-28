from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency exists in normal installs
    load_dotenv = None


@dataclass(frozen=True)
class Config:
    api_key: str | None
    base_url: str
    model: str
    max_steps: int
    workspace: Path


def load_config(workspace: Path | None = None) -> Config:
    if load_dotenv is not None:
        load_dotenv()

    root = (workspace or Path.cwd()).resolve()
    max_steps_raw = os.getenv("NANOCODE_MAX_STEPS", "20")
    try:
        max_steps = int(max_steps_raw)
    except ValueError:
        max_steps = 20

    return Config(
        api_key=os.getenv("NANOCODE_API_KEY"),
        base_url=os.getenv("NANOCODE_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("NANOCODE_MODEL", "gpt-4o-mini"),
        max_steps=max(1, max_steps),
        workspace=root,
    )

