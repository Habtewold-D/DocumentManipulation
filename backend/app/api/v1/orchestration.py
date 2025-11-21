from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.orchestration.repository import CommandRunRepository
from app.orchestration.schemas import CommandRequest, CommandResponse
from app.orchestration.service import OrchestrationService

router = APIRouter()


@router.post("/documents/{document_id}/commands", response_model=CommandResponse)
def run_command(
    document_id: str,
    payload: CommandRequest,
    db: Session = Depends(get_db),
) -> CommandResponse:
    service = OrchestrationService(CommandRunRepository(db))
    return service.run_command(document_id, payload.command)
