from app.db.models.document_version import DocumentVersion
from app.domain.documents.repository import DocumentRepository
from app.domain.versions.retention import VersionRetentionService
from app.domain.versions.repository import VersionRepository
from app.domain.versions.schemas import VersionItem
from app.orchestration.repository import CommandRunRepository
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

        self.repository.db.commit()
        return self._to_item(accepted)

    def reject_draft(self, document_id: str, draft_id: str) -> VersionItem:
        draft = self.repository.get_for_document(document_id, draft_id)
        if not draft:
            raise ValueError("Draft not found")
        if draft.state != "draft":
            raise ValueError(f"Only draft versions can be rejected. Current state: {draft.state}")

        rejected = self.repository.update_state(draft, "rejected")

        # Delete uploaded image if present
        if draft.image_url and self.cloudinary_client:
            try:
                # Parse public_id from url
                url_parts = draft.image_url.split('/upload/')
                if len(url_parts) > 1:
                    after_upload = url_parts[1]
                    path_parts = after_upload.split('/')
                    if len(path_parts) > 1:
                        public_id = '/'.join(path_parts[1:])  # Skip version
                        self.cloudinary_client.delete_asset(public_id)
            except Exception:
                pass  # Ignore errors when deleting image

        self.repository.db.commit()
        return self._to_item(rejected)

    def insert_image_into_pdf(self, document_id: str, page_number: int, position: str, image_url: str) -> str:
        current_version = self.repository.get_current_for_document(document_id)
        if not current_version or not current_version.pdf_asset_id:
            raise ValueError("No current PDF version")

        pdf_data = self.cloudinary_client.download_asset(current_version.pdf_asset_id)

        import requests
        image_response = requests.get(image_url)
        image_data = image_response.content

        import fitz
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        if page_number > len(doc):
            raise ValueError("Page number out of range")

        page = doc[page_number - 1]

        import io
        from PIL import Image
        image = Image.open(io.BytesIO(image_data))
        width, height = image.size

        # Assume position "top" is top left
        rect = fitz.Rect(0, 0, width, height)
        page.insert_image(rect, stream=image_data)

        output = doc.tobytes()
        asset_id = self.cloudinary_client.upload_asset(output, "application/pdf", filename=f"{document_id}_inserted.pdf")
        return asset_id
