"""
Health check endpoint (in-memory store).
"""
from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "/",
    summary="Health check",
    description="Returns system health including model and database status.",
)
async def health():
    settings = get_settings()

    # Model status
    model_status: dict = {}
    try:
        from app.ml.model_loader import get_registry
        registry = get_registry()
        model_status = registry.health()
        models_ok = all(v == "loaded" for v in model_status.values())
    except RuntimeError:
        models_ok = False
        model_status = {"error": "models_not_loaded"}

    # DB status -- in-memory store is always available
    db_ok = True

    overall = "healthy" if (db_ok and models_ok) else "degraded"

    return {
        "status": overall,
        "version": settings.app_version,
        "model_version": settings.model_version,
        "database": "connected" if db_ok else "unavailable",
        "models": model_status,
    }