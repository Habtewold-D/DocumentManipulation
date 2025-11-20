from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.tool_execution_log import ToolExecutionLog


class ToolLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_document(self, document_id: str) -> list[ToolExecutionLog]:
        stmt = (
            select(ToolExecutionLog)
            .where(ToolExecutionLog.document_id == document_id)
            .order_by(ToolExecutionLog.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def save(self, log: ToolExecutionLog) -> ToolExecutionLog:
        self.db.add(log)
        self.db.flush()
        return log
