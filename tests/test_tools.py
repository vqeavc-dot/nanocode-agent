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



def test_list_symbols_finds_python_functions_and_classes(tmp_path: Path):
    (tmp_path / "module.py").write_text(
        "class Service:\n    def run(self):\n        return 1\n\ndef helper():\n    return 2\n",
        encoding="utf-8",
    )
    tools = LocalTools(tmp_path)

    result = tools.list_symbols("module.py")

    assert result.ok
    assert "module.py:1: class Service" in result.content
    assert "module.py:2: def run" in result.content
    assert "module.py:5: def helper" in result.content


def test_run_command_can_require_user_confirmation(tmp_path: Path):
    tools = LocalTools(tmp_path, confirm_commands=True, confirmer=lambda command: False)

    result = tools.run_command("python --version")

    assert not result.ok
    assert "rejected by user confirmation" in result.content


def test_repo_map_tool_returns_compact_structure(tmp_path: Path):
    (tmp_path / "app.py").write_text("import os\n\ndef main():\n    return os.getcwd()\n", encoding="utf-8")
    tools = LocalTools(tmp_path)

    result = tools.repo_map(".")

    assert result.ok
    assert "Repo map for ." in result.content
    assert "app.py" in result.content
    assert "imports: os" in result.content
    assert "def main" in result.content


def test_apply_patch_file_applies_unified_diff(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("def value():\n    return 1\n", encoding="utf-8")
    tools = LocalTools(tmp_path)
    patch = """--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def value():
-    return 1
+    return 2
"""

    result = tools.apply_patch_file("app.py", patch)

    assert result.ok
    assert "return 2" in path.read_text(encoding="utf-8")
    assert "Applied patch" in result.content


def test_apply_patch_file_rejects_context_mismatch(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("def value():\n    return 1\n", encoding="utf-8")
    tools = LocalTools(tmp_path)
    patch = """--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def missing():
-    return 1
+    return 2
"""

    result = tools.apply_patch_file("app.py", patch)

    assert not result.ok
    assert "context mismatch" in result.content
    assert path.read_text(encoding="utf-8") == "def value():\n    return 1\n"


def test_apply_patch_file_rolls_back_invalid_python(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("def value():\n    return 1\n", encoding="utf-8")
    tools = LocalTools(tmp_path)
    patch = """--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def value():
-    return 1
+    return (
"""

    result = tools.apply_patch_file("app.py", patch)

    assert not result.ok
    assert "syntax check failed" in result.content
    assert path.read_text(encoding="utf-8") == "def value():\n    return 1\n"


def test_run_dispatch_includes_repo_map_and_patch(tmp_path: Path):
    (tmp_path / "app.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    tools = LocalTools(tmp_path)

    repo_result = tools.run("repo_map", {"path": "."})
    patch_result = tools.run(
        "apply_patch_file",
        {
            "path": "app.py",
            "patch": "--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n def value():\n-    return 1\n+    return 3\n",
        },
    )

    assert repo_result.ok
    assert patch_result.ok
    assert "return 3" in (tmp_path / "app.py").read_text(encoding="utf-8")


def test_search_code_ranks_filename_and_symbol_matches(tmp_path: Path):
    (tmp_path / "plain.py").write_text("value = 'target'\n", encoding="utf-8")
    (tmp_path / "target_service.py").write_text("def target():\n    return 1\n", encoding="utf-8")
    tools = LocalTools(tmp_path)

    result = tools.search_code("target")

    assert result.ok
    assert result.content.splitlines()[0].startswith("target_service.py:1")


def test_search_code_limits_matches_per_file(tmp_path: Path):
    (tmp_path / "many.py").write_text("\n".join("target" for _ in range(20)), encoding="utf-8")
    tools = LocalTools(tmp_path)

    result = tools.search_code("target", limit=20)

    assert result.ok
    assert result.content.count("many.py") == 5


def test_tool_catalog_matches_schema_names(tmp_path: Path):
    tools = LocalTools(tmp_path)
    catalog_names = [item["name"] for item in tools.tool_catalog()]
    schema_names = [item["function"]["name"] for item in tools.schemas()]

    assert catalog_names == schema_names
    assert {item["stage"] for item in tools.tool_catalog()} >= {"context", "edit", "verify", "safety", "finish"}
    assert all("risk" in item for item in tools.tool_catalog())


def test_inspect_git_status_outside_git_is_safe(tmp_path: Path):
    result = LocalTools(tmp_path).inspect_git_status()

    assert result.ok
    assert "Not a Git repository" in result.content


def test_run_tests_rejects_non_test_command(tmp_path: Path):
    result = LocalTools(tmp_path).run_tests("python --version")

    assert not result.ok
    assert "test-oriented" in result.content


def test_secret_scan_does_not_print_secret_value(tmp_path: Path):
    fake_secret = "sk-" + "abcdefghijklmnopqrstuvwxyz"
    (tmp_path / ".env").write_text(f"NANOCODE_API_KEY={fake_secret}\n", encoding="utf-8")

    result = LocalTools(tmp_path).secret_scan(".")

    assert not result.ok
    assert "likely secret" in result.content
    assert fake_secret not in result.content
