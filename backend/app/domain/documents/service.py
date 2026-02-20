from datetime import UTC

from app.db.models.document import Document
from app.domain.documents.repository import DocumentRepository
from app.domain.documents.schemas import DocumentSummary, UploadDocumentResult
from app.domain.versions.repository import VersionRepository
from app.storage.asset_service import AssetService
from app.storage.cloudinary_client import CloudinaryClient


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        asset_service: AssetService | None = None,
        cloudinary_client: CloudinaryClient | None = None,
        version_repository: VersionRepository | None = None,
    ) -> None:
        self.repository = repository
        self.asset_service = asset_service
        self.cloudinary_client = cloudinary_client
        self.version_repository = version_repository

    def _build_download_url(self, asset_id: str | None) -> str | None:
        if not asset_id or self.cloudinary_client is None:
            return None
        try:
            return self.cloudinary_client.build_download_url(asset_id)
        except Exception:
            return None

    def _to_summary(self, document: Document) -> DocumentSummary:
        original_url = self._build_download_url(document.original_asset_id)

        current_url: str | None = None
        if document.current_version_id and self.version_repository is not None:
            current_version = self.version_repository.get_for_document(document.id, document.current_version_id)
            if current_version and current_version.pdf_asset_id:
                current_url = self._build_download_url(current_version.pdf_asset_id)

        return DocumentSummary(
            document_id=document.id,
            name=document.name,
            original_url=original_url,
            current_url=current_url,
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
