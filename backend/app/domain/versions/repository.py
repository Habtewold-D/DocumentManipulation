from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.document_version import DocumentVersion


class VersionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_document(self, document_id: str) -> list[DocumentVersion]:
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
        )
        return list(self.db.scalars(stmt).all())

    def next_version_number(self, document_id: str) -> int:
        stmt = select(func.max(DocumentVersion.version_number)).where(DocumentVersion.document_id == document_id)
        max_number = self.db.execute(stmt).scalar_one_or_none()
        return (max_number or 0) + 1

    def save(self, version: DocumentVersion) -> DocumentVersion:
        self.db.add(version)
        self.db.flush()
        return version

    def get_for_document(self, document_id: str, version_id: str) -> DocumentVersion | None:
        stmt = select(DocumentVersion).where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.id == version_id,
        )
        return self.db.scalars(stmt).first()

    def update_state(self, version: DocumentVersion, new_state: str) -> DocumentVersion:
        version.state = new_state
        self.db.add(version)
        self.db.flush()
        return version
