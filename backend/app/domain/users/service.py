from app.auth.security import hash_password, verify_password
from app.db.models.user import User
from app.domain.users.repository import UserRepository
from app.domain.users.schemas import UserCreate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def register(self, payload: UserCreate) -> User:
        existing = self.repository.get_by_email(payload.email)
        if existing:
            raise ValueError("Email already registered")
        password_hash = hash_password(payload.password)
        return self.repository.create(payload.email, password_hash, payload.full_name)

    def authenticate(self, email: str, password: str) -> User:
        user = self.repository.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        return user
