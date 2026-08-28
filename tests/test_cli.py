from __future__ import annotations

from pathlib import Path

from nanocode.cli import collect_git_diff_summary, format_usage


def test_format_usage_displays_token_counts():
    assert format_usage({"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}) == (
        "Token usage: prompt=1, completion=2, total=3"
    )


def test_collect_git_diff_summary_returns_empty_outside_git(tmp_path: Path):
    assert collect_git_diff_summary(tmp_path) == ""
