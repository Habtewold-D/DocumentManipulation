from typing import Any
from urllib.request import urlopen

import cloudinary
import cloudinary.uploader
import cloudinary.utils

from app.config.settings import settings


class CloudinaryClient:
    def __init__(self) -> None:
        if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
            raise ValueError("Cloudinary credentials are not configured")

        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )

    def upload_pdf(self, file_bytes: bytes, public_id: str, folder: str = "pdf-agent/originals") -> dict[str, Any]:
        response = cloudinary.uploader.upload(
            file_bytes,
            resource_type="raw",
            public_id=public_id,
            folder=folder,
            overwrite=False,
            invalidate=False,
            use_filename=False,
        )
        return {
            "asset_id": response.get("public_id"),
            "version": response.get("version"),
            "secure_url": response.get("secure_url"),
            "bytes": response.get("bytes"),
            "format": response.get("format"),
            "resource_type": response.get("resource_type"),
        }

    def upload_version_pdf(self, file_bytes: bytes, public_id: str, folder: str = "pdf-agent/versions") -> dict[str, Any]:
        return self.upload_pdf(file_bytes=file_bytes, public_id=public_id, folder=folder)

    def upload_image(self, file_bytes: bytes, public_id: str, folder: str = "pdf-agent/images") -> dict[str, Any]:
        response = cloudinary.uploader.upload(
            file_bytes,
            resource_type="image",
            public_id=public_id,
            folder=folder,
            overwrite=False,
            invalidate=False,
            use_filename=False,
        )
        return {
            "asset_id": response.get("public_id"),
            "version": response.get("version"),
            "secure_url": response.get("secure_url"),
            "bytes": response.get("bytes"),
            "format": response.get("format"),
            "resource_type": response.get("resource_type"),
        }

    def build_download_url(self, asset_id: str, version: str | int | None = None) -> str:
        public_id = asset_id
        options: dict[str, Any] = {"resource_type": "raw", "secure": True}
        if version is not None:
            options["version"] = version
        url, _ = cloudinary.utils.cloudinary_url(public_id, **options)
        return url

    def delete_asset(self, asset_id: str) -> dict[str, Any]:
        return cloudinary.uploader.destroy(asset_id, resource_type="raw", invalidate=True)

    def download_asset_bytes(self, asset_id: str, version: str | int | None = None) -> bytes:
        url = self.build_download_url(asset_id=asset_id, version=version)
        with urlopen(url) as response:
            return response.read()
