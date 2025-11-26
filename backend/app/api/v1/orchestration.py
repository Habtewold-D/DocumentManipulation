from fastapi import APIRouter, Depends, Header, HTTPException
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
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> CommandResponse:
    service = OrchestrationService(CommandRunRepository(db))
    try:
        return service.run_command(document_id, payload.command, idempotency_key=idempotency_key)
    except ValueError as error:
        message = str(error)
        if message == "Document not found":
            raise HTTPException(status_code=404, detail=message) from error
        raise HTTPException(status_code=409, detail=message) from error
