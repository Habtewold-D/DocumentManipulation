from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.compare import CompareResponse, CompareService
from app.domain.versions.repository import VersionRepository

router = APIRouter()


@router.get("/documents/{document_id}/compare", response_model=CompareResponse)
def compare_versions(
    document_id: str,
    from_version: str,
    to_version: str,
    db: Session = Depends(get_db),
) -> CompareResponse:
    compare_service = CompareService(VersionRepository(db))
    try:
        return compare_service.compare(document_id, from_version, to_version)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
