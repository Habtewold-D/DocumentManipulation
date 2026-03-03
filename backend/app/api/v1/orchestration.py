import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.jobs.queue import cancel_queued_run, enqueue_run_processing
from app.orchestration.repository import CommandRunRepository
from app.orchestration.schemas import CommandRequest, CommandResponse, CommandRunItem
from app.orchestration.service import OrchestrationService

router = APIRouter()
logger = logging.getLogger(__name__)


def _enqueue_or_fallback_inline(run_id: str) -> None:
    try:
        enqueue_run_processing(run_id)
    except Exception as error:
        logger.warning("Queue enqueue failed for run_id=%s, falling back to inline processing: %s", run_id, error)
        OrchestrationService.process_queued_run(run_id)


@router.post("/documents/{document_id}/commands", response_model=CommandResponse)
def run_command(
    document_id: str,
    payload: CommandRequest,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    service = OrchestrationService(CommandRunRepository(db))
    try:
        response = service.enqueue_command(document_id, payload.command, image_url=payload.imageUrl, idempotency_key=idempotency_key)
        _enqueue_or_fallback_inline(response.run_id)
        return response
    except RuntimeError as error:
        return JSONResponse(
            status_code=503,
            content={"error": str(error)},
        )
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
        run = service.cancel_run(run_id)
        cancel_queued_run(run_id)
        return run
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        message = str(error)
        status_code = 404 if message == "Run not found" else 409
        raise HTTPException(status_code=status_code, detail=message) from error


@router.post("/commands/{run_id}/retry", response_model=CommandRunItem)
def retry_run(run_id: str, db: Session = Depends(get_db)) -> CommandRunItem:
    service = OrchestrationService(CommandRunRepository(db))
    try:
        run = service.retry_run(run_id)
        _enqueue_or_fallback_inline(run.run_id)
        return run
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        message = str(error)
        status_code = 404 if message == "Run not found" else 409
        raise HTTPException(status_code=status_code, detail=message) from error
