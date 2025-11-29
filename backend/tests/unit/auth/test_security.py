import pytest

from app.auth.security import TokenError, create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_and_verify_roundtrip() -> None:
    password = "super-secret"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash) is True


def test_decode_access_token_returns_subject() -> None:
    token = create_access_token("user-123", expires_minutes=5)

    subject = decode_access_token(token)

    assert subject == "user-123"


def test_decode_access_token_rejects_invalid_token() -> None:
    with pytest.raises(TokenError):
        decode_access_token("invalid.token.value")
