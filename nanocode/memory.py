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
    selected_files: list[str] = field(default_factory=list)
    task_profile: str = ""
    plan: str = ""
    verification: str = ""

    def add(self, tool: str, content: str, ok: bool = True) -> None:
        self.observations.append(Observation(tool=tool, content=content, ok=ok))

    def note_file(self, path: str) -> None:
        normalized = path.replace("\\", "/")
        if normalized not in self.selected_files:
            self.selected_files.append(normalized)

    def set_task_profile(self, profile: str) -> None:
        self.task_profile = profile

    def set_plan(self, plan: str) -> None:
        self.plan = plan

    def set_verification(self, verification: str) -> None:
        self.verification = verification

    def as_messages(self) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if self.task_profile:
            messages.append({"role": "user", "content": f"Task profile memory:\n{self.task_profile}"})
        if self.plan:
            messages.append({"role": "user", "content": f"Plan memory:\n{self.plan}"})
        if self.selected_files:
            messages.append({"role": "user", "content": "Selected files:\n" + "\n".join(self.selected_files[-12:])})
        if self.verification:
            messages.append({"role": "user", "content": f"Verification memory:\n{self.verification}"})
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
