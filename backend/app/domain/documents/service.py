from datetime import UTC, datetime
from uuid import uuid4

from app.db.models.document import Document
from app.domain.documents.repository import DocumentRepository
from app.domain.documents.schemas import DocumentSummary, UploadDocumentResult


class DocumentService:
    def __init__(self, repository: DocumentRepository) -> None:
        self.repository = repository

    @staticmethod
    def _to_summary(document: Document) -> DocumentSummary:
        return DocumentSummary(
            document_id=document.id,
            name=document.name,
            created_at=document.created_at,
        )

    def upload(self, filename: str | None) -> UploadDocumentResult:
        return UploadDocumentResult(
            document_id=str(uuid4()),
            name=filename or "untitled.pdf",
            created_at=datetime.now(UTC),
        )

    def list(self, owner_id: str) -> list[DocumentSummary]:
        documents = self.repository.list_by_owner(owner_id)
        return [self._to_summary(document) for document in documents]

    def get(self, document_id: str) -> DocumentSummary | None:
        document = self.repository.get(document_id)
        if not document:
            return None
        return self._to_summary(document)
