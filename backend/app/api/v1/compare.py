from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class CompareResponse(BaseModel):
    document_id: str
    from_version: str
    to_version: str
    changed_pages: list[int]


@router.get("/documents/{document_id}/compare", response_model=CompareResponse)
def compare_versions(document_id: str, from_version: str, to_version: str) -> CompareResponse:
    return CompareResponse(
        document_id=document_id,
        from_version=from_version,
        to_version=to_version,
        changed_pages=[],
    )
