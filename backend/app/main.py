from fastapi import FastAPI

from app.api.router import api_router
from app.config.settings import settings


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name)
    application.include_router(api_router, prefix="/api")

    @application.get("/")
    def root() -> dict[str, str]:
        return {"service": settings.app_name, "status": "ok"}

    return application


app = create_app()
