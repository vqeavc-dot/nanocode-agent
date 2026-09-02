from __future__ import annotations

from pathlib import Path

from nanocode.ui import run_agent_from_payload


class FakeConfig:
    api_key = "key"
    base_url = "https://example.test"
    model = "model"
    max_steps = 3


class FakeResult:
    final = "done"
    steps = 1
    stopped_by_limit = False
    transcript = ["[step 1] tool_call final_answer args={}"]
    usage = {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}


def test_run_agent_payload_requires_task(tmp_path: Path):
    result = run_agent_from_payload(FakeConfig(), tmp_path, {"task": ""})
    assert not result["ok"]
    assert "task is required" in result["error"]


def test_ui_contains_preset_buttons_and_metrics():
    from nanocode.ui import HTML

    assert "data-preset=\"map\"" in HTML
    assert "<option value=\"review\">Review</option>" in HTML
    assert "<option value=\"trust\">Trust</option>" in HTML
    assert "countPlans" in HTML
    assert "[verify]" in HTML
    assert "countTools" in HTML
    assert "Git diff summary" in HTML
