import json

from pydantic import BaseModel

from app.domain.versions.repository import VersionRepository


class CompareResponse(BaseModel):
    document_id: str
    from_version: str
    to_version: str
    changed_pages: list[int]


class CompareService:
    def __init__(self, version_repository: VersionRepository) -> None:
        self.version_repository = version_repository

    @staticmethod
    def _extract_page_hashes(preview_manifest: str | None) -> dict[int, str]:
        if not preview_manifest:
            return {}
        try:
            parsed = json.loads(preview_manifest)
        except json.JSONDecodeError:
            return {}

        pages = parsed.get("pages", []) if isinstance(parsed, dict) else []
        page_hashes: dict[int, str] = {}
        for item in pages:
            if not isinstance(item, dict):
                continue
            page_number = item.get("page")
            page_hash = item.get("hash")
            if isinstance(page_number, int) and isinstance(page_hash, str):
                page_hashes[page_number] = page_hash
        return page_hashes

    def compare(self, document_id: str, from_version: str, to_version: str) -> CompareResponse:
        source = self.version_repository.get_for_document(document_id, from_version)
        target = self.version_repository.get_for_document(document_id, to_version)
        if not source or not target:
            raise ValueError("Version not found")

        source_hashes = self._extract_page_hashes(source.preview_manifest)
        target_hashes = self._extract_page_hashes(target.preview_manifest)

        page_numbers = set(source_hashes.keys()) | set(target_hashes.keys())
        changed_pages = sorted(
            [page for page in page_numbers if source_hashes.get(page) != target_hashes.get(page)]
        )

        return CompareResponse(
            document_id=document_id,
            from_version=from_version,
            to_version=to_version,
            changed_pages=changed_pages,
        )
