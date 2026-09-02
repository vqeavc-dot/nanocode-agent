from nanocode.failure import analyze_failure


def test_failure_analyzer_classifies_patch_context_mismatch():
    analysis = analyze_failure("apply_patch_file", "Patch context mismatch")

    assert analysis.kind == "edit_context_mismatch"
    assert "Re-open" in analysis.suggestion


def test_failure_analyzer_classifies_unsafe_command():
    analysis = analyze_failure("run_command", "Command blocked by safety policy")

    assert analysis.kind == "unsafe_command"
