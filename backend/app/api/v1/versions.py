from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import SessionLocal
from app.db.session import get_db
from app.domain.documents.repository import DocumentRepository
from app.domain.logs.repository import ToolLogRepository
from app.domain.versions.retention import VersionRetentionService
from app.domain.versions.repository import VersionRepository
from app.domain.versions.schemas import VersionItem
from app.domain.versions.service import VersionService
from app.storage.cloudinary_client import CloudinaryClient

router = APIRouter()


def _run_retention_cleanup(document_id: str) -> None:
    db = SessionLocal()
    try:
        retention = VersionRetentionService(VersionRepository(db), ToolLogRepository(db), CloudinaryClient())
        retention.cleanup_rejected_immediately(document_id)
        retention.cleanup_stale_drafts()
        retention.keep_latest_five_accepted(document_id)
        db.commit()
    finally:
        db.close()


@router.get("/documents/{document_id}/versions", response_model=list[VersionItem])
def list_versions(document_id: str, db: Session = Depends(get_db)) -> list[VersionItem]:
    cloudinary_client: CloudinaryClient | None
    try:
        cloudinary_client = CloudinaryClient()
    except ValueError:
        cloudinary_client = None

    service = VersionService(
        VersionRepository(db),
        DocumentRepository(db),
        cloudinary_client=cloudinary_client,
    )
    return service.list_versions(document_id)


@router.post("/documents/{document_id}/drafts/{draft_id}/accept", response_model=VersionItem)
def accept_draft(
    document_id: str,
    draft_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> VersionItem:
    retention = VersionRetentionService(VersionRepository(db), ToolLogRepository(db), CloudinaryClient())
    service = VersionService(
        VersionRepository(db),
        DocumentRepository(db),
        retention,
        cloudinary_client=CloudinaryClient(),
    )
    try:
        result = service.accept_draft(document_id, draft_id)
        background_tasks.add_task(_run_retention_cleanup, document_id)
        return result
    except ValueError as error:
        message = str(error)
        if message == "Draft not found" or message == "Document not found":
            raise HTTPException(status_code=404, detail=message) from error
        raise HTTPException(status_code=409, detail=message) from error


@router.post("/documents/{document_id}/drafts/{draft_id}/reject", response_model=VersionItem)
def reject_draft(
    document_id: str,
    draft_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> VersionItem:
    retention = VersionRetentionService(VersionRepository(db), ToolLogRepository(db), CloudinaryClient())
    service = VersionService(
        VersionRepository(db),
        DocumentRepository(db),
        retention,
        cloudinary_client=CloudinaryClient(),
    )
    try:
        result = service.reject_draft(document_id, draft_id)
        background_tasks.add_task(_run_retention_cleanup, document_id)
        return result
    except ValueError as error:
        message = str(error)
        if message == "Draft not found":
            raise HTTPException(status_code=404, detail=message) from error
        raise HTTPException(status_code=409, detail=message) from error


@router.get("/documents/{document_id}/versions/{version_id}/preview")
def preview_version(
    document_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> Response:
    document = DocumentRepository(db).get_for_owner(user_id, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    version = VersionRepository(db).get_for_document(document_id, version_id)
    if not version or not version.pdf_asset_id:
        raise HTTPException(status_code=404, detail="Version preview not found")

    cloudinary_client = CloudinaryClient()
    try:
        pdf_bytes = cloudinary_client.download_asset_bytes(version.pdf_asset_id)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Failed to download preview: {error}") from error

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=version-preview.pdf"},
    )
