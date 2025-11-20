from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.documents.repository import DocumentRepository
from app.domain.documents.schemas import DocumentSummary, UploadDocumentResult
from app.domain.documents.service import DocumentService

router = APIRouter()


@router.post("/documents/upload", response_model=UploadDocumentResult)
async def upload_document(file: UploadFile, db: Session = Depends(get_db)) -> UploadDocumentResult:
    service = DocumentService(DocumentRepository(db))
    return service.upload(file.filename)


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
