from __future__ import annotations

from dataclasses import dataclass

from .skills import Skill, SkillRegistry
from .task_classifier import TaskProfile, classify_task


@dataclass(frozen=True)
class Plan:
    steps: list[str]
    profile: TaskProfile
    skill: Skill

    def render(self) -> str:
        header = [self.profile.render(), self.skill.render(), "Plan:"]
        body = [f"{index}. {step}" for index, step in enumerate(self.steps, start=1)]
        return "\n".join([*header, *body])


class LightweightPlanner:
    """A deterministic planner that gives the ReAct loop a small initial map."""

    def __init__(self, skills: SkillRegistry | None = None):
        self.skills = skills or SkillRegistry()

    def build(self, task: str) -> Plan:
        profile = classify_task(task)
        skill = self.skills.select(profile)
        lowered = task.lower()
        steps = [
            "Start from the selected skill workflow instead of free-form tool wandering.",
            "Build a compact repo_map or list/search relevant files before opening broad context.",
            "Inspect only the most relevant file windows and tool observations.",
        ]
        if any(word in lowered for word in ["change", "update", "fix", "add", "implement", "修改", "修复", "新增", "实现"]):
            steps.append("Apply the smallest safe edit, preferring apply_patch_file for line-oriented code changes.")
        if any(word in lowered for word in ["test", "pytest", "verify", "run", "测试", "验证", "运行"]):
            steps.append("Run the relevant test or verification command and use failures as feedback.")
        else:
            steps.append("Run a lightweight syntax check or targeted test when the task changes code.")
        if profile.risk == "high":
            steps.append("Keep the change narrow, inspect git status, and avoid broad rewrites without explicit evidence.")
        steps.append("Finish with final_answer that summarizes files touched, verification, diff, and any limitation.")
        return Plan(steps, profile=profile, skill=skill)
