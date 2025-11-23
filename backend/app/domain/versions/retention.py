from datetime import UTC, datetime, timedelta

from app.domain.logs.repository import ToolLogRepository
from app.domain.versions.repository import VersionRepository
from app.storage.cloudinary_client import CloudinaryClient


class VersionRetentionService:
    def __init__(
        self,
        version_repository: VersionRepository,
        tool_log_repository: ToolLogRepository,
        cloudinary_client: CloudinaryClient,
    ) -> None:
        self.version_repository = version_repository
        self.tool_log_repository = tool_log_repository
        self.cloudinary_client = cloudinary_client

    def cleanup_stale_drafts(self) -> None:
        threshold = datetime.now(UTC) - timedelta(hours=24)
        stale_drafts = self.version_repository.list_stale_drafts(threshold)
        for version in stale_drafts:
            self._delete_version_assets(version.pdf_asset_id)
            self.tool_log_repository.delete_for_version(version.id)
            self.version_repository.delete_by_id(version.id)

    def cleanup_rejected_immediately(self, document_id: str) -> None:
        rejected = self.version_repository.list_by_state(document_id=document_id, state="rejected")
        for version in rejected:
            self._delete_version_assets(version.pdf_asset_id)
            self.tool_log_repository.delete_for_version(version.id)
            self.version_repository.delete_by_id(version.id)

    def keep_latest_five_accepted(self, document_id: str) -> None:
        old_accepted = self.version_repository.list_accepted_older_than_keep(document_id=document_id, keep_count=5)
        for version in old_accepted:
            self._delete_version_assets(version.pdf_asset_id)
            self.tool_log_repository.delete_for_version(version.id)
            self.version_repository.delete_by_id(version.id)

    def _delete_version_assets(self, asset_id: str | None) -> None:
        if not asset_id:
            return
        try:
            self.cloudinary_client.delete_asset(asset_id)
        except Exception:
            return
