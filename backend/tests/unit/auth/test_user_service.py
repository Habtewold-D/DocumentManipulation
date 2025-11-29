import pytest

from app.domain.users.schemas import UserCreate
from app.domain.users.service import UserService


class _FakeUser:
    def __init__(self, email: str, password_hash: str):
        self.id = "user-1"
        self.email = email
        self.password_hash = password_hash
        self.full_name = None
        self.created_at = None


class _FakeUserRepo:
    def __init__(self):
        self.by_email = {}

    def get_by_email(self, email: str):
        return self.by_email.get(email)

    def create(self, email: str, password_hash: str, full_name: str | None = None):
        user = _FakeUser(email=email, password_hash=password_hash)
        user.full_name = full_name
        self.by_email[email] = user
        return user


def test_register_creates_user() -> None:
    repo = _FakeUserRepo()
    service = UserService(repo)  # type: ignore[arg-type]

    user = service.register(UserCreate(email="a@b.com", password="secret123", full_name="A"))

    assert user.email == "a@b.com"


def test_register_rejects_duplicate_email() -> None:
    repo = _FakeUserRepo()
    service = UserService(repo)  # type: ignore[arg-type]
    service.register(UserCreate(email="a@b.com", password="secret123", full_name="A"))

    with pytest.raises(ValueError):
        service.register(UserCreate(email="a@b.com", password="secret123", full_name="A"))
