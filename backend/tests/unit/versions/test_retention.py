from datetime import UTC, datetime, timedelta

from app.domain.versions.retention import VersionRetentionService


class _FakeVersion:
    def __init__(self, version_id: str, asset_id: str | None = None, created_at: datetime | None = None):
        self.id = version_id
        self.pdf_asset_id = asset_id
        self.created_at = created_at or datetime.now(UTC)


class _FakeVersionRepo:
    def __init__(self):
        now = datetime.now(UTC)
        self.rejected = [_FakeVersion("rejected-1", "asset-r")]
        self.accepted = [
            _FakeVersion("a1"),
            _FakeVersion("a2"),
            _FakeVersion("a3"),
            _FakeVersion("a4"),
            _FakeVersion("a5"),
            _FakeVersion("a6"),
        ]
        self.stale = [_FakeVersion("draft-1", "asset-d", now - timedelta(hours=30))]
        self.deleted = []

    def list_stale_drafts(self, older_than):
        _ = older_than
        return self.stale

    def list_by_state(self, document_id: str, state: str):
        _ = document_id
        if state == "rejected":
            return self.rejected
        return []

    def list_accepted_older_than_keep(self, document_id: str, keep_count: int):
        _ = document_id
        return self.accepted[keep_count:]

    def delete_by_id(self, version_id: str):
        self.deleted.append(version_id)


class _FakeToolLogRepo:
    def __init__(self):
        self.deleted_for = []

    def delete_for_version(self, version_id: str):
        self.deleted_for.append(version_id)


class _FakeCloudinary:
    def __init__(self):
        self.deleted_assets = []

    def delete_asset(self, asset_id: str):
        self.deleted_assets.append(asset_id)


def test_retention_cleanup_applies_all_rules() -> None:
    version_repo = _FakeVersionRepo()
    log_repo = _FakeToolLogRepo()
    cloudinary = _FakeCloudinary()
    service = VersionRetentionService(version_repo, log_repo, cloudinary)  # type: ignore[arg-type]

    service.cleanup_stale_drafts()
    service.cleanup_rejected_immediately("doc-1")
    service.keep_latest_five_accepted("doc-1")

    assert "draft-1" in version_repo.deleted
    assert "rejected-1" in version_repo.deleted
    assert "a6" in version_repo.deleted
    assert "asset-d" in cloudinary.deleted_assets
    assert "asset-r" in cloudinary.deleted_assets
