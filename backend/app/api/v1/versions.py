from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class VersionItem(BaseModel):
    version_id: str
    state: str
    created_at: datetime


@router.get("/documents/{document_id}/versions", response_model=list[VersionItem])
def list_versions(document_id: str) -> list[VersionItem]:
    return [
        VersionItem(
            version_id=str(uuid4()),
            state="accepted",
            created_at=datetime.now(UTC),
        )
    ]


@router.post("/documents/{document_id}/drafts/{draft_id}/accept", response_model=VersionItem)
def accept_draft(document_id: str, draft_id: str) -> VersionItem:
    return VersionItem(
        version_id=draft_id,
        state="accepted",
        created_at=datetime.now(UTC),
    )


@router.post("/documents/{document_id}/drafts/{draft_id}/reject", response_model=VersionItem)
def reject_draft(document_id: str, draft_id: str) -> VersionItem:
    return VersionItem(
        version_id=draft_id,
        state="rejected",
        created_at=datetime.now(UTC),
    )
