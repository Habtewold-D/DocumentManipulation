from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.config.settings import settings

class CommandRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)
        self.requests: dict[str, deque[datetime]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/commands") and request.method.upper() == "POST":
            client_key = request.client.host if request.client else "unknown"
            now = datetime.utcnow()
            window_start = now - timedelta(minutes=1)
            entries = self.requests[client_key]

            while entries and entries[0] < window_start:
                entries.popleft()

            if len(entries) >= settings.command_rate_limit_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "rate_limited",
                            "message": "Too many command requests. Please retry later.",
                        }
                    },
                )

            entries.append(now)

        return await call_next(request)


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )
    application.add_middleware(CommandRateLimitMiddleware)
    application.include_router(api_router, prefix="/api")

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": str(exc),
                }
            },
        )

    @application.get("/")
    def root() -> dict[str, str]:
        return {"service": settings.app_name, "status": "ok"}

    return application


app = create_app()
