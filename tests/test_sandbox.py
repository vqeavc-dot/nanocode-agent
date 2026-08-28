from pathlib import Path

import pytest

from nanocode.sandbox import Sandbox, SandboxError, assert_command_safe


def test_resolve_path_allows_workspace_file(tmp_path: Path):
    sandbox = Sandbox(tmp_path)
    assert sandbox.resolve_path("src/app.py") == tmp_path / "src" / "app.py"


def test_resolve_path_blocks_parent_escape(tmp_path: Path):
    sandbox = Sandbox(tmp_path)
    with pytest.raises(SandboxError):
        sandbox.resolve_path("../outside.txt")


def test_resolve_path_blocks_absolute_escape(tmp_path: Path):
    sandbox = Sandbox(tmp_path)
    outside = tmp_path.parent / "outside.txt"
    with pytest.raises(SandboxError):
        sandbox.resolve_path(outside)


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard HEAD",
        "rm -rf .",
        "del /s /q *",
        "Remove-Item . -Recurse",
    ],
)
def test_dangerous_commands_are_blocked(command: str):
    with pytest.raises(SandboxError):
        assert_command_safe(command)


def test_normal_command_is_allowed():
    assert_command_safe("python --version")

