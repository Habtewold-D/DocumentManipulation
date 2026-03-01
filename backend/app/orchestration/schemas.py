from datetime import datetime

from pydantic import BaseModel


class CommandRequest(BaseModel):
    command: str


class CommandResponse(BaseModel):
    run_id: str
    status: str
    draft_version_id: str
    created_at: datetime
    error: str | None = None
    execution_mode: str | None = None


class CommandRunItem(BaseModel):
    run_id: str
    document_id: str
    command_text: str
    status: str
    draft_version_id: str
    created_at: datetime
    error: str | None = None
    execution_mode: str | None = None
