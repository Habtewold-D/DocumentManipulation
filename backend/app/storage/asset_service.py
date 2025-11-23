from uuid import uuid4

from app.storage.cloudinary_client import CloudinaryClient


class AssetService:
    def __init__(self, cloudinary_client: CloudinaryClient) -> None:
        self.cloudinary = cloudinary_client

    def upload_original_pdf(self, file_bytes: bytes, filename: str) -> dict:
        safe_name = filename.rsplit(".", maxsplit=1)[0].strip().replace(" ", "-") or "document"
        public_id = f"doc-{safe_name}-{uuid4()}"
        return self.cloudinary.upload_pdf(file_bytes=file_bytes, public_id=public_id, folder="pdf-agent/originals")
