from fastapi import APIRouter
from app.orchestration.schemas import CommandRequest, CommandResponse
from app.orchestration.service import OrchestrationService

router = APIRouter()
orchestration_service = OrchestrationService()


@router.post("/documents/{document_id}/commands", response_model=CommandResponse)
def run_command(document_id: str, payload: CommandRequest) -> CommandResponse:
    return orchestration_service.run_command(document_id, payload.command)
