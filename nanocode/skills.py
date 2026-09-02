from __future__ import annotations

from dataclasses import dataclass

from .task_classifier import TaskProfile, TaskType


@dataclass(frozen=True)
class Skill:
    name: str
    purpose: str
    steps: tuple[str, ...]

    def render(self) -> str:
        lines = [f"Selected skill: {self.name}", f"Purpose: {self.purpose}"]
        lines.extend(f"- {step}" for step in self.steps)
        return "\n".join(lines)


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[TaskType, Skill] = {
            "explain": Skill(
                "code_question",
                "Answer code questions without unnecessary edits.",
                ("repo_map", "search_code", "view_file", "final_answer"),
            ),
            "bug_fix": Skill(
                "bug_fix",
                "Repair failing behavior with environment feedback.",
                ("repo_map", "search_code", "view_file", "apply_patch_file", "run_tests", "failure_analysis", "final_answer"),
            ),
            "feature": Skill(
                "feature_change",
                "Add focused behavior and verify it with tests.",
                ("repo_map", "inspect related tests", "apply_patch_file", "run_tests", "final_answer"),
            ),
            "test": Skill(
                "test_work",
                "Add or run tests around existing behavior.",
                ("repo_map", "view_file", "write or patch tests", "run_tests", "final_answer"),
            ),
            "review": Skill(
                "code_review",
                "Inspect changes and report risks before edits.",
                ("inspect_git_status", "repo_map", "view_file", "secret_scan", "final_answer"),
            ),
            "refactor": Skill(
                "safe_refactor",
                "Make behavior-preserving changes under stricter verification.",
                ("inspect_git_status", "repo_map", "search_code", "apply_patch_file", "run_tests", "secret_scan", "final_answer"),
            ),
        }

    def select(self, profile: TaskProfile) -> Skill:
        return self._skills[profile.task_type]

    def all(self) -> list[Skill]:
        return list(self._skills.values())
