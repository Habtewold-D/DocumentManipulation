from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.command_run import CommandRun


class CommandRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, run_id: str) -> CommandRun | None:
        stmt = select(CommandRun).where(CommandRun.id == run_id)
        return self.db.scalars(stmt).first()

    def save(self, run: CommandRun) -> CommandRun:
        self.db.add(run)
        self.db.flush()
        return run
