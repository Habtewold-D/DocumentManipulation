from datetime import datetime

from sqlalchemy import delete, func, select
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

    def list_by_state(self, document_id: str, state: str) -> list[DocumentVersion]:
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id, DocumentVersion.state == state)
            .order_by(DocumentVersion.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def list_stale_drafts(self, older_than: datetime) -> list[DocumentVersion]:
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.state == "draft", DocumentVersion.created_at < older_than)
            .order_by(DocumentVersion.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_accepted_older_than_keep(self, document_id: str, keep_count: int) -> list[DocumentVersion]:
        accepted = self.list_by_state(document_id=document_id, state="accepted")
        if len(accepted) <= keep_count:
            return []
        return accepted[keep_count:]

    def delete_by_id(self, version_id: str) -> None:
        stmt = delete(DocumentVersion).where(DocumentVersion.id == version_id)
        self.db.execute(stmt)
