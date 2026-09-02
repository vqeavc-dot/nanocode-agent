import pytest

from nanocode.modes import resolve_mode


def test_review_mode_is_conservative_default():
    policy = resolve_mode(None)

    assert policy.name == "review"
    assert policy.confirm_commands
    assert not policy.allow_auto_commit


def test_trust_mode_allows_automation():
    policy = resolve_mode("trust")

    assert policy.name == "trust"
    assert not policy.confirm_commands
    assert policy.allow_auto_commit


def test_invalid_mode_is_rejected():
    with pytest.raises(ValueError):
        resolve_mode("anything")
