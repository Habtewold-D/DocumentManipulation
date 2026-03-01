from __future__ import annotations

from app.config.settings import settings


def _require_rq_dependencies() -> None:
    try:
        import redis  # noqa: F401
        import rq  # noqa: F401
    except Exception as error:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "Worker queue dependencies are not available. Install backend dependencies with rq and redis."
        ) from error


def _get_redis_connection():
    _require_rq_dependencies()
    import redis

    return redis.from_url(settings.queue_redis_url)


def _get_queue():
    _require_rq_dependencies()
    import rq

    return rq.Queue(
        name=settings.queue_name,
        connection=_get_redis_connection(),
        default_timeout=settings.queue_job_timeout_seconds,
    )


def enqueue_run_processing(run_id: str) -> str:
    queue = _get_queue()

    # Deduplicate by using run_id as job id so retries/enqueues are idempotent.
    existing = queue.fetch_job(run_id)
    if existing is not None and existing.get_status(refresh=False) not in {"finished", "failed", "stopped", "canceled"}:
        return existing.id

    job = queue.enqueue(
        "app.orchestration.service.OrchestrationService.process_queued_run",
        run_id,
        job_id=run_id,
    )
    return job.id


def cancel_queued_run(run_id: str) -> None:
    _require_rq_dependencies()
    from rq.command import send_stop_job_command
    from rq.job import Job

    connection = _get_redis_connection()

    try:
        send_stop_job_command(connection, run_id)
    except Exception:
        pass

    try:
        job = Job.fetch(run_id, connection=connection)
        if job.get_status(refresh=False) in {"queued", "deferred", "scheduled"}:
            job.cancel()
    except Exception:
        pass
