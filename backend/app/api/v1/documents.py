from fastapi import APIRouter, UploadFile
from app.domain.documents.schemas import DocumentSummary, UploadDocumentResult
from app.domain.documents.service import DocumentService

router = APIRouter()

document_service = DocumentService()


@router.post("/documents/upload", response_model=UploadDocumentResult)
async def upload_document(file: UploadFile) -> UploadDocumentResult:
    return document_service.upload(file.filename)


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents() -> list[DocumentSummary]:
    return document_service.list()


@router.get("/documents/{document_id}", response_model=DocumentSummary)
def get_document(document_id: str) -> DocumentSummary:
    return document_service.get(document_id)
