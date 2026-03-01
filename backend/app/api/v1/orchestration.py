from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.orchestration.repository import CommandRunRepository
from app.orchestration.schemas import CommandRequest, CommandResponse, CommandRunItem
from app.orchestration.service import OrchestrationService

router = APIRouter()


@router.post("/documents/{document_id}/commands", response_model=CommandResponse)
def run_command(
    document_id: str,
    payload: CommandRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    service = OrchestrationService(CommandRunRepository(db))
    try:
        response = service.enqueue_command(document_id, payload.command, idempotency_key=idempotency_key)
        background_tasks.add_task(OrchestrationService.process_queued_run, response.run_id)
        return response
    except ValueError as error:
        message = str(error)
        status_code = 404 if message == "Document not found" else 400
        return JSONResponse(
            status_code=status_code,
            content={"error": message}
        )


@router.get("/commands/{run_id}", response_model=CommandRunItem)
def get_run(run_id: str, db: Session = Depends(get_db)) -> CommandRunItem:
    service = OrchestrationService(CommandRunRepository(db))
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/documents/{document_id}/commands", response_model=list[CommandRunItem])
def list_document_runs(document_id: str, limit: int = 20, db: Session = Depends(get_db)) -> list[CommandRunItem]:
    service = OrchestrationService(CommandRunRepository(db))
    bounded_limit = max(1, min(limit, 100))
    return service.list_runs(document_id=document_id, limit=bounded_limit)


@router.post("/commands/{run_id}/cancel", response_model=CommandRunItem)
def cancel_run(run_id: str, db: Session = Depends(get_db)) -> CommandRunItem:
    service = OrchestrationService(CommandRunRepository(db))
    try:
        return service.cancel_run(run_id)
    except ValueError as error:
        message = str(error)
        status_code = 404 if message == "Run not found" else 409
        raise HTTPException(status_code=status_code, detail=message) from error


@router.post("/commands/{run_id}/retry", response_model=CommandRunItem)
def retry_run(run_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> CommandRunItem:
    service = OrchestrationService(CommandRunRepository(db))
    try:
        run = service.retry_run(run_id)
        background_tasks.add_task(OrchestrationService.process_queued_run, run.run_id)
        return run
    except ValueError as error:
        message = str(error)
        status_code = 404 if message == "Run not found" else 409
        raise HTTPException(status_code=status_code, detail=message) from error
