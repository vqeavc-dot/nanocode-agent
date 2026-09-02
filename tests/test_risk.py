from nanocode.modes import resolve_mode
from nanocode.risk import decide_tool_risk, risk_for_tool


def test_risk_policy_marks_patch_as_medium():
    assert risk_for_tool("apply_patch_file") == "medium"


def test_review_mode_requires_confirmation_for_medium_risk_tool():
    decision = decide_tool_risk("apply_patch_file", resolve_mode("review"))

    assert decision.allowed
    assert decision.requires_confirmation


def test_trust_mode_allows_medium_risk_without_confirmation():
    decision = decide_tool_risk("apply_patch_file", resolve_mode("trust"))

    assert decision.allowed
    assert not decision.requires_confirmation
