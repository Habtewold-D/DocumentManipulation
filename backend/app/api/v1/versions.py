from fastapi import APIRouter
from app.domain.versions.schemas import VersionItem
from app.domain.versions.service import VersionService

router = APIRouter()
version_service = VersionService()


@router.get("/documents/{document_id}/versions", response_model=list[VersionItem])
def list_versions(document_id: str) -> list[VersionItem]:
    return version_service.list_versions(document_id)


@router.post("/documents/{document_id}/drafts/{draft_id}/accept", response_model=VersionItem)
def accept_draft(document_id: str, draft_id: str) -> VersionItem:
    _ = document_id
    return version_service.accept_draft(draft_id)


@router.post("/documents/{document_id}/drafts/{draft_id}/reject", response_model=VersionItem)
def reject_draft(document_id: str, draft_id: str) -> VersionItem:
    _ = document_id
    return version_service.reject_draft(draft_id)
