from datetime import UTC, datetime
from uuid import uuid4

from app.db.models.document_version import DocumentVersion
from app.domain.versions.repository import VersionRepository
from app.domain.versions.schemas import VersionItem


class VersionService:
    def __init__(self, repository: VersionRepository) -> None:
        self.repository = repository

    @staticmethod
    def _to_item(version: DocumentVersion) -> VersionItem:
        return VersionItem(
            version_id=version.id,
            state=version.state,
            created_at=version.created_at,
        )

    def list_versions(self, document_id: str) -> list[VersionItem]:
        versions = self.repository.list_for_document(document_id)
        return [self._to_item(version) for version in versions]

    def accept_draft(self, draft_id: str) -> VersionItem:
        return VersionItem(
            version_id=draft_id,
            state="accepted",
            created_at=datetime.now(UTC),
        )

    def reject_draft(self, draft_id: str) -> VersionItem:
        return VersionItem(
            version_id=draft_id,
            state="rejected",
            created_at=datetime.now(UTC),
        )
