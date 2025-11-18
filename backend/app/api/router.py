from fastapi import APIRouter

from app.api.v1.compare import router as compare_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.logs import router as logs_router
from app.api.v1.orchestration import router as orchestration_router
from app.api.v1.tools import router as tools_router
from app.api.v1.versions import router as versions_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/v1", tags=["health"])
api_router.include_router(tools_router, prefix="/v1", tags=["tools"])
api_router.include_router(documents_router, prefix="/v1", tags=["documents"])
api_router.include_router(versions_router, prefix="/v1", tags=["versions"])
api_router.include_router(compare_router, prefix="/v1", tags=["compare"])
api_router.include_router(logs_router, prefix="/v1", tags=["logs"])
api_router.include_router(orchestration_router, prefix="/v1", tags=["orchestration"])
