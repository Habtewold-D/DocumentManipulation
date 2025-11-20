from datetime import UTC, datetime
from uuid import uuid4

from app.db.models.tool_execution_log import ToolExecutionLog
from app.domain.logs.repository import ToolLogRepository
from app.domain.logs.schemas import ToolLogItem


class ToolLogService:
    def __init__(self, repository: ToolLogRepository) -> None:
        self.repository = repository

    @staticmethod
    def _to_item(log: ToolExecutionLog) -> ToolLogItem:
        return ToolLogItem(
            log_id=log.id,
            tool=log.tool_name,
            status=log.status,
            created_at=log.created_at,
        )

    def list_logs(self, document_id: str) -> list[ToolLogItem]:
        logs = self.repository.list_for_document(document_id)
        return [self._to_item(log) for log in logs]
