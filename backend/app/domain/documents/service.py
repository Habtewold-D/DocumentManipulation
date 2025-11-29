from datetime import UTC

from app.db.models.document import Document
from app.domain.documents.repository import DocumentRepository
from app.domain.documents.schemas import DocumentSummary, UploadDocumentResult
from app.storage.asset_service import AssetService


class DocumentService:
    def __init__(self, repository: DocumentRepository, asset_service: AssetService | None = None) -> None:
        self.repository = repository
        self.asset_service = asset_service

    @staticmethod
    def _to_summary(document: Document) -> DocumentSummary:
        return DocumentSummary(
            document_id=document.id,
            name=document.name,
            created_at=document.created_at,
        )

    def upload(self, owner_id: str, filename: str | None, file_bytes: bytes) -> UploadDocumentResult:
        if self.asset_service is None:
            raise ValueError("Asset service is required for upload")

        safe_name = filename or "untitled.pdf"
        uploaded = self.asset_service.upload_original_pdf(file_bytes=file_bytes, filename=safe_name)

        if not uploaded.get("asset_id"):
            raise ValueError("Cloudinary upload failed")

        document = self.repository.create(
            owner_id=owner_id,
            name=safe_name,
            original_asset_id=uploaded["asset_id"],
        )
        self.repository.db.commit()

        return UploadDocumentResult(
            document_id=document.id,
            name=document.name,
            original_asset_id=document.original_asset_id,
            original_url=uploaded.get("secure_url", ""),
            created_at=document.created_at,
        )

    def list(self, owner_id: str) -> list[DocumentSummary]:
        documents = self.repository.list_by_owner(owner_id)
        return [self._to_summary(document) for document in documents]

    def get(self, owner_id: str, document_id: str) -> DocumentSummary | None:
        document = self.repository.get_for_owner(owner_id, document_id)
        if not document:
            return None
        return self._to_summary(document)
