from pathlib import Path

from nanocode.tools import LocalTools


def test_list_files(tmp_path: Path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    tools = LocalTools(tmp_path)
    result = tools.list_files(".")
    assert result.ok
    assert "a.txt" in result.content


def test_search_code_finds_match(tmp_path: Path):
    (tmp_path / "app.py").write_text("def target():\n    return 1\n", encoding="utf-8")
    tools = LocalTools(tmp_path)
    result = tools.search_code("target")
    assert result.ok
    assert "app.py:1" in result.content


def test_view_file_returns_window(tmp_path: Path):
    lines = "\n".join(f"line {i}" for i in range(1, 121))
    (tmp_path / "long.txt").write_text(lines, encoding="utf-8")
    tools = LocalTools(tmp_path)
    result = tools.view_file("long.txt", start_line=11, limit=5)
    assert result.ok
    assert "11: line 11" in result.content
    assert "15: line 15" in result.content
    assert "16: line 16" not in result.content


def test_edit_file_replaces_unique_text(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("def value():\n    return 1\n", encoding="utf-8")
    tools = LocalTools(tmp_path)
    result = tools.edit_file("app.py", "return 1", "return 2")
    assert result.ok
    assert "return 2" in path.read_text(encoding="utf-8")


def test_edit_file_rejects_missing_text(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("x = 1\n", encoding="utf-8")
    tools = LocalTools(tmp_path)
    result = tools.edit_file("app.py", "x = 2", "x = 3")
    assert not result.ok


def test_edit_file_rejects_multiple_matches(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("x = 1\nx = 1\n", encoding="utf-8")
    tools = LocalTools(tmp_path)
    result = tools.edit_file("app.py", "x = 1", "x = 2")
    assert not result.ok


def test_write_file_creates_file(tmp_path: Path):
    tools = LocalTools(tmp_path)
    result = tools.write_file("src/new.py", "value = 1\n")
    assert result.ok
    assert (tmp_path / "src" / "new.py").exists()


def test_write_file_rejects_invalid_python_and_rolls_back(tmp_path: Path):
    tools = LocalTools(tmp_path)
    result = tools.write_file("bad.py", "def nope(:\n")
    assert not result.ok
    assert not (tmp_path / "bad.py").exists()


def test_run_command_executes_simple_command(tmp_path: Path):
    tools = LocalTools(tmp_path)
    result = tools.run_command("python --version")
    assert result.ok
    assert "Python" in result.content

