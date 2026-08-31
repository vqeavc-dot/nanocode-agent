from __future__ import annotations

from pathlib import Path

from nanocode.cli import auto_commit_changes, collect_git_diff_summary, format_usage


def test_format_usage_displays_token_counts():
    assert format_usage({"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}) == (
        "Token usage: prompt=1, completion=2, total=3"
    )


def test_collect_git_diff_summary_returns_empty_outside_git(tmp_path: Path):
    assert collect_git_diff_summary(tmp_path) == ""


class CommitResult:
    final = "Update files"
    stopped_by_limit = False
    transcript = ["[step 1] observation run_command ok=True: pytest 1 passed"]


class UntestedResult:
    final = "Update files"
    stopped_by_limit = False
    transcript = []


def test_auto_commit_skips_without_successful_test(tmp_path: Path):
    assert "no successful test" in auto_commit_changes(tmp_path, UntestedResult())


def test_auto_commit_skips_outside_git(tmp_path: Path):
    assert "not a Git repository" in auto_commit_changes(tmp_path, CommitResult())
