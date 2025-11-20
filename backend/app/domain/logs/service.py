from datetime import UTC, datetime
from uuid import uuid4

from app.domain.logs.schemas import ToolLogItem


class ToolLogService:
    def list_logs(self, document_id: str) -> list[ToolLogItem]:
        _ = document_id
        return [
            ToolLogItem(
                log_id=str(uuid4()),
                tool="replace_text",
                status="success",
                created_at=datetime.now(UTC),
            )
        ]
