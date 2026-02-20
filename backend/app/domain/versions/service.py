from app.db.models.document_version import DocumentVersion
from app.domain.documents.repository import DocumentRepository
from app.domain.versions.retention import VersionRetentionService
from app.domain.versions.repository import VersionRepository
from app.domain.versions.schemas import VersionItem
from app.storage.cloudinary_client import CloudinaryClient


class VersionService:
    def __init__(
        self,
        repository: VersionRepository,
        document_repository: DocumentRepository,
        retention_service: VersionRetentionService | None = None,
        cloudinary_client: CloudinaryClient | None = None,
    ) -> None:
        self.repository = repository
        self.document_repository = document_repository
        self.retention_service = retention_service
        self.cloudinary_client = cloudinary_client

    def _build_download_url(self, asset_id: str | None) -> str | None:
        if not asset_id or self.cloudinary_client is None:
            return None
        try:
            return self.cloudinary_client.build_download_url(asset_id)
        except Exception:
            return None

    def _to_item(self, version: DocumentVersion) -> VersionItem:
        return VersionItem(
            version_id=version.id,
            state=version.state,
            pdf_url=self._build_download_url(version.pdf_asset_id),
            created_at=version.created_at,
        )

    def list_versions(self, document_id: str) -> list[VersionItem]:
        versions = self.repository.list_for_document(document_id)
        return [self._to_item(version) for version in versions]

    def accept_draft(self, document_id: str, draft_id: str) -> VersionItem:
        draft = self.repository.get_for_document(document_id, draft_id)
        if not draft:
            raise ValueError("Draft not found")
        if draft.state != "draft":
            raise ValueError(f"Only draft versions can be accepted. Current state: {draft.state}")

        accepted = self.repository.update_state(draft, "accepted")
        document = self.document_repository.set_current_version(document_id, accepted.id)
        if not document:
            raise ValueError("Document not found")

        if self.retention_service:
            self.retention_service.cleanup_stale_drafts()
            self.retention_service.keep_latest_five_accepted(document_id)
        self.repository.db.commit()
        return self._to_item(accepted)

    def reject_draft(self, document_id: str, draft_id: str) -> VersionItem:
        draft = self.repository.get_for_document(document_id, draft_id)
        if not draft:
            raise ValueError("Draft not found")
        if draft.state != "draft":
            raise ValueError(f"Only draft versions can be rejected. Current state: {draft.state}")

        rejected = self.repository.update_state(draft, "rejected")
        if self.retention_service:
            self.retention_service.cleanup_rejected_immediately(document_id)
            self.retention_service.cleanup_stale_drafts()
        self.repository.db.commit()
        return self._to_item(rejected)
