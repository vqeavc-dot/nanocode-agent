from nanocode.skills import SkillRegistry
from nanocode.task_classifier import classify_task


def test_skill_registry_selects_bug_fix_workflow():
    skill = SkillRegistry().select(classify_task("fix failing calculator test"))

    assert skill.name == "bug_fix"
    assert "run_tests" in skill.steps


def test_skill_registry_exposes_all_core_workflows():
    names = {skill.name for skill in SkillRegistry().all()}

    assert {"code_question", "bug_fix", "feature_change", "test_work", "code_review", "safe_refactor"} <= names
