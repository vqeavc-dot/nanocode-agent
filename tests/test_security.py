from pathlib import Path

from nanocode.security import is_protected_path, redact_secrets


def test_redact_secrets_masks_key_values():
    fake_secret = "sk-" + "abcdefghijklmnopqrstuvwxyz"
    bearer = "token123456"
    text = f"NANOCODE_API_KEY={fake_secret} and Authorization: Bearer {bearer}"

    redacted = redact_secrets(text)

    assert fake_secret not in redacted
    assert bearer not in redacted
    assert "[REDACTED" in redacted


def test_is_protected_path_detects_env_files():
    assert is_protected_path(Path(".env"))
    assert not is_protected_path(Path(".env.example"))
