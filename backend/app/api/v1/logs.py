from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.logs.repository import ToolLogRepository
from app.domain.logs.schemas import ToolLogItem
from app.domain.logs.service import ToolLogService

router = APIRouter()


@router.get("/documents/{document_id}/tool-logs", response_model=list[ToolLogItem])
def get_tool_logs(document_id: str, db: Session = Depends(get_db)) -> list[ToolLogItem]:
    service = ToolLogService(ToolLogRepository(db))
    return service.list_logs(document_id)
