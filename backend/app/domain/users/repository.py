from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.scalars(stmt).first()

    def get_by_id(self, user_id: str) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return self.db.scalars(stmt).first()

    def create(self, email: str, password_hash: str, full_name: str | None = None) -> User:
        user = User(email=email, full_name=full_name, password_hash=password_hash)
        self.db.add(user)
        self.db.flush()
        return user
