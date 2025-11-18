from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class CommandRequest(BaseModel):
    command: str


class CommandResponse(BaseModel):
    run_id: str
    status: str
    draft_version_id: str
    created_at: datetime


@router.post("/documents/{document_id}/commands", response_model=CommandResponse)
def run_command(document_id: str, payload: CommandRequest) -> CommandResponse:
    _ = payload.command
    return CommandResponse(
        run_id=str(uuid4()),
        status="draft_ready",
        draft_version_id=str(uuid4()),
        created_at=datetime.now(UTC),
    )
