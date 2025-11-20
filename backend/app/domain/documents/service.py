from datetime import UTC, datetime
from uuid import uuid4

from app.domain.documents.schemas import DocumentSummary, UploadDocumentResult


class DocumentService:
    def upload(self, filename: str | None) -> UploadDocumentResult:
        return UploadDocumentResult(
            document_id=str(uuid4()),
            name=filename or "untitled.pdf",
            created_at=datetime.now(UTC),
        )

    def list(self) -> list[DocumentSummary]:
        return []

    def get(self, document_id: str) -> DocumentSummary:
        return DocumentSummary(
            document_id=document_id,
            name="document.pdf",
            created_at=datetime.now(UTC),
        )
