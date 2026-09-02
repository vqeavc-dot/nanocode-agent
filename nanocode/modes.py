from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


RunMode = Literal["review", "trust"]


@dataclass(frozen=True)
class ModePolicy:
    name: RunMode
    confirm_commands: bool
    allow_auto_commit: bool
    prompt_note: str

    def render(self) -> str:
        return (
            f"Mode: {self.name}\n"
            f"- confirm_commands={self.confirm_commands}\n"
            f"- allow_auto_commit={self.allow_auto_commit}\n"
            f"- {self.prompt_note}"
        )


def resolve_mode(name: str | None) -> ModePolicy:
    normalized = (name or "review").strip().lower()
    if normalized == "trust":
        return ModePolicy(
            name="trust",
            confirm_commands=False,
            allow_auto_commit=True,
            prompt_note="Trust mode may run safe local commands without extra confirmation and may auto-commit after successful tests.",
        )
    if normalized == "review":
        return ModePolicy(
            name="review",
            confirm_commands=True,
            allow_auto_commit=False,
            prompt_note="Review mode favors human inspection: show plan, observations, diff, and require confirmation before shell commands.",
        )
    raise ValueError("mode must be 'review' or 'trust'")
