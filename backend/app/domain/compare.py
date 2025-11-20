from pydantic import BaseModel


class CompareResponse(BaseModel):
    document_id: str
    from_version: str
    to_version: str
    changed_pages: list[int]


class CompareService:
    def compare(self, document_id: str, from_version: str, to_version: str) -> CompareResponse:
        return CompareResponse(
            document_id=document_id,
            from_version=from_version,
            to_version=to_version,
            changed_pages=[],
        )
