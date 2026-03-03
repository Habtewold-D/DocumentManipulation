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

    def create(
        self,
        document_id: str,
        command_text: str,
        image_url: str | None = None,
        idempotency_key: str | None = None,
    ) -> CommandRun:
        run = CommandRun(
            document_id=document_id,
            command_text=command_text,
            image_url=image_url,
            idempotency_key=idempotency_key,
        )
        return run

    def get_by_idempotency_key(self, document_id: str, idempotency_key: str) -> CommandRun | None:
        stmt = select(CommandRun).where(
            CommandRun.document_id == document_id,
            CommandRun.idempotency_key == idempotency_key,
        )
        return self.db.scalars(stmt).first()

    def list_for_document(self, document_id: str, limit: int = 20) -> list[CommandRun]:
        stmt = (
            select(CommandRun)
            .where(CommandRun.document_id == document_id)
            .order_by(CommandRun.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
