from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.document import Document


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_owner(self, owner_id: str) -> list[Document]:
        stmt = select(Document).where(Document.owner_id == owner_id).order_by(Document.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get(self, document_id: str) -> Document | None:
        stmt = select(Document).where(Document.id == document_id)
        return self.db.scalars(stmt).first()

    def save(self, document: Document) -> Document:
        self.db.add(document)
        self.db.flush()
        return document

    def set_current_version(self, document_id: str, version_id: str) -> Document | None:
        document = self.get(document_id)
        if not document:
            return None
        document.current_version_id = version_id
        self.db.add(document)
        self.db.flush()
        return document
