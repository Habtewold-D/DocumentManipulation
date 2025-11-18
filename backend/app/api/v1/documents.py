from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel

router = APIRouter()


class DocumentSummary(BaseModel):
    document_id: str
    name: str
    created_at: datetime


@router.post("/documents/upload", response_model=DocumentSummary)
async def upload_document(file: UploadFile) -> DocumentSummary:
    return DocumentSummary(
        document_id=str(uuid4()),
        name=file.filename or "untitled.pdf",
        created_at=datetime.now(UTC),
    )


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents() -> list[DocumentSummary]:
    return []


@router.get("/documents/{document_id}", response_model=DocumentSummary)
def get_document(document_id: str) -> DocumentSummary:
    return DocumentSummary(
        document_id=document_id,
        name="document.pdf",
        created_at=datetime.now(UTC),
    )
