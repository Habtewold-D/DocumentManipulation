from datetime import UTC, datetime
from uuid import uuid4

from app.domain.versions.schemas import VersionItem


class VersionService:
    def list_versions(self, document_id: str) -> list[VersionItem]:
        _ = document_id
        return [
            VersionItem(
                version_id=str(uuid4()),
                state="accepted",
                created_at=datetime.now(UTC),
            )
        ]

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
