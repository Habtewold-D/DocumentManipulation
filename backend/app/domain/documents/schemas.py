from datetime import datetime

from pydantic import BaseModel


class DocumentSummary(BaseModel):
    document_id: str
    name: str
    created_at: datetime


class UploadDocumentResult(BaseModel):
    document_id: str
    name: str
    original_asset_id: str
    original_url: str
    created_at: datetime
