import json
from pathlib import Path
from typing import Any

from nanocode.agent import CodingAgent
from nanocode.tools import LocalTools


class FakeModel:
    def __init__(self):
        self.calls = 0

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]):
        self.calls += 1
        if self.calls == 1:
            return _response("view_file", {"path": "app.py"})
        if self.calls == 2:
            return _response("edit_file", {"path": "app.py", "old_text": "return 1", "new_text": "return 2"})
        if self.calls == 3:
            return _response("run_command", {"command": "python -m py_compile app.py"})
        return _response("final_answer", {"summary": "Changed value to 2 and syntax check passed."})


def _response(name: str, args: dict[str, Any]):
    return type(
        "Response",
        (),
        {
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"call_{name}",
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)},
                    }
                ],
            },
        },
    )()


def test_agent_loop_runs_tools_until_final_answer(tmp_path: Path):
    (tmp_path / "app.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    agent = CodingAgent(model=FakeModel(), tools=LocalTools(tmp_path), max_steps=5)

    result = agent.run("Change value to 2")

    assert not result.stopped_by_limit
    assert result.final == "Changed value to 2 and syntax check passed."
    assert "return 2" in (tmp_path / "app.py").read_text(encoding="utf-8")
    assert result.transcript[0].startswith("[mode]")
    assert result.transcript[1].startswith("[plan]")


def test_agent_verbose_records_each_tool_event(tmp_path: Path, capsys):
    (tmp_path / "app.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    agent = CodingAgent(model=FakeModel(), tools=LocalTools(tmp_path), max_steps=5, verbose=True)

    result = agent.run("Change value to 2")
    output = capsys.readouterr().out

    assert "tool_call view_file" in output
    assert "tool_call edit_file" in output
    assert "tool_call run_command" in output
    assert any("observation run_command ok=True" in event for event in result.transcript)
    assert any(event.startswith("[verify]") for event in result.transcript)


def test_agent_aggregates_token_usage(tmp_path: Path):
    (tmp_path / "app.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    agent = CodingAgent(model=FakeModel(), tools=LocalTools(tmp_path), max_steps=5)

    result = agent.run("Change value to 2")

    assert result.usage["prompt_tokens"] == 40
    assert result.usage["completion_tokens"] == 20
    assert result.usage["total_tokens"] == 60
