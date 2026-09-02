from pathlib import Path

from nanocode.repo_map import RepoMap, summarize_java, summarize_javascript_like, summarize_python


def test_python_summary_extracts_imports_classes_functions_and_methods():
    imports, symbols = summarize_python(
        "import os\nfrom pathlib import Path\n\nclass Service:\n    def run(self):\n        pass\n\ndef helper():\n    pass\n"
    )

    assert imports == ["os", "pathlib"]
    assert "line 4: class Service" in symbols
    assert "line 5: method Service.run" in symbols
    assert "line 8: def helper" in symbols


def test_javascript_summary_extracts_imports_and_symbols():
    imports, symbols = summarize_javascript_like(
        "import api from './api';\nconst fs = require('fs');\nexport function run() {}\nexport class Widget {}\nconst load = () => 1;\n"
    )

    assert imports == ["./api", "fs"]
    assert "line 3: function run" in symbols
    assert "line 4: class Widget" in symbols
    assert "line 5: function load" in symbols


def test_java_summary_extracts_imports_types_and_methods():
    imports, symbols = summarize_java(
        "import java.util.List;\npublic class App {\n  public static void main(String[] args) { }\n}\n"
    )

    assert imports == ["java.util.List"]
    assert "line 2: type App" in symbols
    assert "line 3: method main" in symbols


def test_repo_map_skips_ignored_dirs_and_large_files(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def keep():\n    pass\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "skip.js").write_text("function hidden() {}\n", encoding="utf-8")
    (tmp_path / "src" / "large.py").write_text("x = 1\n" * 50, encoding="utf-8")

    rendered = RepoMap(tmp_path, max_file_bytes=20).build(".")

    assert "src/app.py" in rendered
    assert "node_modules" not in rendered
    assert "src/large.py" in rendered
    assert "skipped: file too large" in rendered


def test_repo_map_respects_character_budget(tmp_path: Path):
    for idx in range(20):
        (tmp_path / f"m{idx}.py").write_text(f"def f{idx}():\n    pass\n", encoding="utf-8")

    rendered = RepoMap(tmp_path, max_chars=300).build(".")

    assert len(rendered) <= 300
    assert "repo map truncated" in rendered


def test_repo_map_ranks_referenced_file_above_caller(tmp_path: Path):
    (tmp_path / "service.py").write_text("def important():\n    return 1\n", encoding="utf-8")
    (tmp_path / "caller.py").write_text("from service import important\n\ndef run():\n    return important()\n", encoding="utf-8")

    rendered = RepoMap(tmp_path).build(".")
    service_index = rendered.index("service.py")
    caller_index = rendered.index("caller.py")

    assert "ranking=lightweight_def_ref_pagerank" in rendered
    assert service_index < caller_index
    assert "depends_on: service.py" in rendered


def test_repo_map_skips_protected_env_files(tmp_path: Path):
    fake_secret = "sk-" + "secretsecretsecret"
    (tmp_path / ".env").write_text(f"NANOCODE_API_KEY={fake_secret}\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("def value():\n    return 1\n", encoding="utf-8")

    rendered = RepoMap(tmp_path).build(".")

    assert ".env" not in rendered
    assert "app.py" in rendered
