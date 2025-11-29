from app.db.session import SessionLocal
from app.domain.documents.repository import DocumentRepository
from app.domain.logs.repository import ToolLogRepository
from app.domain.versions.repository import VersionRepository
from app.domain.versions.retention import VersionRetentionService
from app.storage.cloudinary_client import CloudinaryClient


def run_cleanup() -> None:
    db = SessionLocal()
    try:
        documents = DocumentRepository(db).list_all()
        retention = VersionRetentionService(
            VersionRepository(db),
            ToolLogRepository(db),
            CloudinaryClient(),
        )

        retention.cleanup_stale_drafts()
        for document in documents:
            retention.cleanup_rejected_immediately(document.id)
            retention.keep_latest_five_accepted(document.id)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run_cleanup()
