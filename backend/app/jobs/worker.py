from __future__ import annotations

from app.config.settings import settings


def run_worker() -> None:
    import redis
    from rq import Worker

    connection = redis.from_url(settings.queue_redis_url)
    worker = Worker([settings.queue_name], connection=connection)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    run_worker()
