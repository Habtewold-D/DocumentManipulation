from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
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
):
    service = OrchestrationService(CommandRunRepository(db))
    try:
        response = service.run_command(document_id, payload.command, idempotency_key=idempotency_key)
        
        # v32.5: If the command failed internally, return a clean error without the 'detail' wrap.
        if response.status == "failed":
            return JSONResponse(
                status_code=400,
                content={"error": response.error or "Command failed"}
            )
            
        return response
    except ValueError as error:
        # v32.5: Clean error formatting for validation or document-not-found errors.
        message = str(error)
        status_code = 404 if message == "Document not found" else 400
        return JSONResponse(
            status_code=status_code,
            content={"error": message}
        )
