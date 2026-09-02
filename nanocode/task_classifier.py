from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


TaskType = Literal["explain", "bug_fix", "feature", "test", "review", "refactor"]
RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class TaskProfile:
    task_type: TaskType
    risk: RiskLevel
    rationale: str

    def render(self) -> str:
        return f"Task profile: type={self.task_type}, risk={self.risk}, rationale={self.rationale}"


def classify_task(task: str) -> TaskProfile:
    lowered = task.lower()
    if any(word in lowered for word in ["refactor", "重构", "rename", "迁移"]):
        return TaskProfile("refactor", "high", "Refactoring can touch broad behavior and needs extra review.")
    if any(word in lowered for word in ["review", "审查", "检查代码", "评价"]):
        return TaskProfile("review", "low", "The user asks to inspect or judge code rather than directly edit it.")
    if any(word in lowered for word in ["fix", "bug", "error", "failed", "修复", "报错"]):
        return TaskProfile("bug_fix", "medium", "The user wants behavior repaired using feedback from failures.")
    if any(word in lowered for word in ["add", "implement", "feature", "新增", "实现", "添加"]):
        return TaskProfile("feature", "medium", "The user wants new behavior, usually requiring implementation and tests.")
    if any(word in lowered for word in ["test", "pytest", "coverage", "测试", "用例"]):
        return TaskProfile("test", "medium", "The user focuses on verification or test coverage.")
    return TaskProfile("explain", "low", "The task appears to be code understanding or explanation.")
