from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.documents.repository import DocumentRepository
from app.domain.documents.schemas import DocumentSummary, UploadDocumentResult
from app.domain.documents.service import DocumentService
from app.storage.asset_service import AssetService
from app.storage.cloudinary_client import CloudinaryClient

router = APIRouter()


@router.post("/documents/upload", response_model=UploadDocumentResult)
async def upload_document(file: UploadFile, db: Session = Depends(get_db)) -> UploadDocumentResult:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        cloudinary_client = CloudinaryClient()
        service = DocumentService(DocumentRepository(db), AssetService(cloudinary_client))
        return service.upload(owner_id="dev-user", filename=file.filename, file_bytes=file_bytes)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentSummary]:
    service = DocumentService(DocumentRepository(db))
    return service.list(owner_id="dev-user")


@router.get("/documents/{document_id}", response_model=DocumentSummary)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentSummary:
    service = DocumentService(DocumentRepository(db))
    document = service.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
