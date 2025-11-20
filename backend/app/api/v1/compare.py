from fastapi import APIRouter
from app.domain.compare import CompareResponse, CompareService

router = APIRouter()
compare_service = CompareService()


@router.get("/documents/{document_id}/compare", response_model=CompareResponse)
def compare_versions(document_id: str, from_version: str, to_version: str) -> CompareResponse:
    return compare_service.compare(document_id, from_version, to_version)
