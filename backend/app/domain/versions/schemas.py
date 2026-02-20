from datetime import datetime

from pydantic import BaseModel


class VersionItem(BaseModel):
    version_id: str
    state: str
    pdf_url: str | None = None
    created_at: datetime
