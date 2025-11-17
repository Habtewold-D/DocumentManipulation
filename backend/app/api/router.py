from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.tools import router as tools_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/v1", tags=["health"])
api_router.include_router(tools_router, prefix="/v1", tags=["tools"])
