from fastapi import APIRouter
from app.domain.logs.schemas import ToolLogItem
from app.domain.logs.service import ToolLogService

router = APIRouter()
tool_log_service = ToolLogService()


@router.get("/documents/{document_id}/tool-logs", response_model=list[ToolLogItem])
def get_tool_logs(document_id: str) -> list[ToolLogItem]:
    return tool_log_service.list_logs(document_id)
