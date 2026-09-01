from nanocode.verifier import inspect_transcript


def test_verifier_detects_successful_pytest_observation():
    signal = inspect_transcript(
        [
            '[step 1] tool_call run_command args={"command": "python -m pytest"}',
            "[step 1] observation run_command ok=True: exit_code=0\nstdout:\n3 passed",
        ]
    )

    assert signal.passed


def test_verifier_rejects_untested_transcript():
    assert not inspect_transcript(["[final] done"]).passed
