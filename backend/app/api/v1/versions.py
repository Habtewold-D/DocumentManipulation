from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.versions.repository import VersionRepository
from app.domain.versions.schemas import VersionItem
from app.domain.versions.service import VersionService

router = APIRouter()


@router.get("/documents/{document_id}/versions", response_model=list[VersionItem])
def list_versions(document_id: str, db: Session = Depends(get_db)) -> list[VersionItem]:
    service = VersionService(VersionRepository(db))
    return service.list_versions(document_id)


@router.post("/documents/{document_id}/drafts/{draft_id}/accept", response_model=VersionItem)
def accept_draft(document_id: str, draft_id: str, db: Session = Depends(get_db)) -> VersionItem:
    _ = document_id
    service = VersionService(VersionRepository(db))
    return service.accept_draft(draft_id)


@router.post("/documents/{document_id}/drafts/{draft_id}/reject", response_model=VersionItem)
def reject_draft(document_id: str, draft_id: str, db: Session = Depends(get_db)) -> VersionItem:
    _ = document_id
    service = VersionService(VersionRepository(db))
    return service.reject_draft(draft_id)
