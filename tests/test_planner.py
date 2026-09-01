from nanocode.planner import LightweightPlanner


def test_planner_mentions_patch_and_tests_for_code_change():
    plan = LightweightPlanner().build("fix calculator and run pytest")
    rendered = plan.render()

    assert "apply_patch_file" in rendered
    assert "test" in rendered.lower()
    assert rendered.startswith("1. ")
