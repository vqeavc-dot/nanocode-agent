from nanocode.memory import Memory


def test_memory_keeps_recent_observations_full():
    memory = Memory(keep_recent=2)
    memory.add("tool1", "old observation " + "x" * 300)
    memory.add("tool2", "recent one")
    memory.add("tool3", "recent two")

    messages = memory.as_messages()
    assert "[summary" in messages[0]["content"]
    assert messages[1]["content"].endswith("recent one")
    assert messages[2]["content"].endswith("recent two")


def test_memory_summary_truncates_old_content():
    memory = Memory(keep_recent=0)
    memory.add("tool", "a" * 300)
    content = memory.as_messages()[0]["content"]
    assert len(content) < 230
    assert content.endswith("...")


def test_memory_tracks_context_decisions():
    memory = Memory()
    memory.set_task_profile("Task profile: type=feature")
    memory.set_plan("Plan: inspect then test")
    memory.note_file("src/app.py")
    memory.set_verification("Verifier: successful test command observed.")

    rendered = "\n".join(message["content"] for message in memory.as_messages())

    assert "Task profile" in rendered
    assert "src/app.py" in rendered
    assert "successful test" in rendered


