from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .modes import ModePolicy


ToolRisk = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    requires_confirmation: bool
    reason: str


TOOL_RISK: dict[str, ToolRisk] = {
    "list_files": "low",
    "search_code": "low",
    "list_symbols": "low",
    "repo_map": "low",
    "view_file": "low",
    "inspect_git_status": "low",
    "secret_scan": "low",
    "run_tests": "low",
    "run_command": "medium",
    "edit_file": "medium",
    "write_file": "medium",
    "apply_patch_file": "medium",
    "final_answer": "low",
}


def risk_for_tool(name: str) -> ToolRisk:
    return TOOL_RISK.get(name, "high")


def decide_tool_risk(name: str, mode: ModePolicy) -> RiskDecision:
    risk = risk_for_tool(name)
    if mode.name == "trust":
        if risk == "high":
            return RiskDecision(False, False, f"{name} is high-risk and is not available in trust mode.")
        return RiskDecision(True, False, f"{name} risk={risk} allowed in trust mode.")
    if risk == "low":
        return RiskDecision(True, False, f"{name} risk=low allowed in review mode.")
    if risk == "medium":
        return RiskDecision(True, True, f"{name} risk=medium requires review-mode confirmation.")
    return RiskDecision(False, False, f"{name} risk=high blocked in review mode.")
