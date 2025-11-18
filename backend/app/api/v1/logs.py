from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ToolLogItem(BaseModel):
    log_id: str
    tool: str
    status: str
    created_at: datetime


@router.get("/documents/{document_id}/tool-logs", response_model=list[ToolLogItem])
def get_tool_logs(document_id: str) -> list[ToolLogItem]:
    return [
        ToolLogItem(
            log_id=str(uuid4()),
            tool="replace_text",
            status="success",
            created_at=datetime.now(UTC),
        )
    ]
