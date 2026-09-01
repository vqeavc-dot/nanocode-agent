from __future__ import annotations

import re
from dataclasses import dataclass


TEST_COMMAND_RE = re.compile(r"\b(pytest|unittest|npm\s+test|pnpm\s+test|yarn\s+test|cargo\s+test|go\s+test|mvn\s+test)\b", re.I)
SUCCESS_RE = re.compile(r"\b(passed|ok|success|successful|0 failed|exit_code=0)\b", re.I)


@dataclass(frozen=True)
class VerificationSignal:
    command_seen: bool
    success_seen: bool

    @property
    def passed(self) -> bool:
        return self.command_seen and self.success_seen

    def render(self) -> str:
        if self.passed:
            return "Verifier: successful test command observed."
        if self.command_seen:
            return "Verifier: test command observed, but success was not proven."
        return "Verifier: no test command observed."


def inspect_transcript(transcript: list[str]) -> VerificationSignal:
    command_seen = False
    success_seen = False
    for event in transcript:
        lowered = event.lower()
        if "run_command" not in lowered:
            continue
        if TEST_COMMAND_RE.search(event) or "test" in lowered:
            command_seen = True
        if "ok=true" in lowered and SUCCESS_RE.search(event):
            success_seen = True
    return VerificationSignal(command_seen=command_seen, success_seen=success_seen)
