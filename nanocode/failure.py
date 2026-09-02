from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailureAnalysis:
    kind: str
    suggestion: str

    def render(self) -> str:
        return f"Failure analysis: kind={self.kind}; suggestion={self.suggestion}"


def analyze_failure(tool: str, content: str) -> FailureAnalysis:
    lowered = content.lower()
    if "context mismatch" in lowered or "old_text was not found" in lowered:
        return FailureAnalysis("edit_context_mismatch", "Re-open the relevant file window, then retry with fresher context or a narrower patch.")
    if "syntax check failed" in lowered or "syntaxerror" in lowered:
        return FailureAnalysis("syntax_error", "Inspect the edited Python block and apply the smallest syntax-correct patch.")
    if tool in {"run_command", "run_tests"} and ("failed" in lowered or "assert" in lowered):
        return FailureAnalysis("test_failure", "Inspect the failing test and the target implementation before changing code again.")
    if "path escapes workspace" in lowered:
        return FailureAnalysis("workspace_escape", "Stay inside the configured workspace and ask the user to change workspace if needed.")
    if "blocked by safety policy" in lowered:
        return FailureAnalysis("unsafe_command", "Use a safer command or ask the user to perform the high-risk action manually.")
    return FailureAnalysis("tool_error", "Use the observation as feedback, narrow context, and re-plan the next tool call.")
