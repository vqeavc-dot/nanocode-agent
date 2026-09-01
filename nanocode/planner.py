from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    steps: list[str]

    def render(self) -> str:
        return "\n".join(f"{index}. {step}" for index, step in enumerate(self.steps, start=1))


class LightweightPlanner:
    """A deterministic planner that gives the ReAct loop a small initial map."""

    def build(self, task: str) -> Plan:
        lowered = task.lower()
        steps = [
            "Build a compact repo_map or list/search relevant files before opening broad context.",
            "Inspect only the most relevant file windows and tool observations.",
        ]
        if any(word in lowered for word in ["change", "update", "fix", "add", "implement", "修改", "修复", "新增", "实现"]):
            steps.append("Apply the smallest safe edit, preferring apply_patch_file for line-oriented code changes.")
        if any(word in lowered for word in ["test", "pytest", "verify", "run", "测试", "验证", "运行"]):
            steps.append("Run the relevant test or verification command and use failures as feedback.")
        else:
            steps.append("Run a lightweight syntax check or targeted test when the task changes code.")
        steps.append("Finish with final_answer that summarizes files touched, verification, diff, and any limitation.")
        return Plan(steps)
