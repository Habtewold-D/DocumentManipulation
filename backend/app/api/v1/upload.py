from fastapi import APIRouter, UploadFile, File, HTTPException

from app.storage.cloudinary_client import CloudinaryClient

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    client = CloudinaryClient()
    try:
        file_bytes = await file.read()
        response = client.upload_image(file_bytes, file.filename)
        return {"url": response["secure_url"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
