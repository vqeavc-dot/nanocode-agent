import json

from nanocode.eval_cases import EvalCase, load_eval_cases, score_transcript


def test_load_eval_cases(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"cases": [{"name": "case", "task": "do it", "expected_tools": ["repo_map"]}]}), encoding="utf-8")

    cases = load_eval_cases(path)

    assert cases == [EvalCase(name="case", task="do it", expected_tools=("repo_map",), safety_expectation="")]


def test_score_transcript_reports_tool_coverage():
    case = EvalCase(name="case", task="do it", expected_tools=("repo_map", "run_tests"))

    score = score_transcript(case, ["[step 1] tool_call repo_map args={}"])

    assert score["tool_coverage"] == 0.5
    assert score["seen_tools"] == ["repo_map"]
