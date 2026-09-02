from nanocode.task_classifier import classify_task


def test_classifier_detects_feature_task_even_when_tests_are_requested():
    profile = classify_task("Add divide support and tests")

    assert profile.task_type == "feature"
    assert profile.risk == "medium"


def test_classifier_detects_pure_test_task():
    profile = classify_task("Run pytest and explain coverage")

    assert profile.task_type == "test"


def test_classifier_marks_refactor_as_high_risk():
    profile = classify_task("Refactor the whole calculator module")

    assert profile.task_type == "refactor"
    assert profile.risk == "high"
