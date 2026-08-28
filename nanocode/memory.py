from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Observation:
    tool: str
    content: str
    ok: bool = True

    def summary(self, limit: int = 180) -> str:
        text = self.content.replace("\n", " ")
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."


@dataclass
class Memory:
    keep_recent: int = 5
    observations: list[Observation] = field(default_factory=list)

    def add(self, tool: str, content: str, ok: bool = True) -> None:
        self.observations.append(Observation(tool=tool, content=content, ok=ok))

    def as_messages(self) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        split_at = max(0, len(self.observations) - self.keep_recent)

        for obs in self.observations[:split_at]:
            messages.append(
                {
                    "role": "user",
                    "content": f"Observation from {obs.tool} [summary ok={obs.ok}]: {obs.summary()}",
                }
            )

        for obs in self.observations[split_at:]:
            messages.append(
                {
                    "role": "user",
                    "content": f"Observation from {obs.tool} [ok={obs.ok}]:\n{obs.content}",
                }
            )

        return messages
