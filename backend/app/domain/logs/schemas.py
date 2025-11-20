from datetime import datetime

from pydantic import BaseModel


class ToolLogItem(BaseModel):
    log_id: str
    tool: str
    status: str
    created_at: datetime
