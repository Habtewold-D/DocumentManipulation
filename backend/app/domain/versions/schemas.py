from datetime import datetime

from pydantic import BaseModel


class VersionItem(BaseModel):
    version_id: str
    state: str
    created_at: datetime
