"""
DeepGuard FastAPI Application Entry Point.

Startup sequence:
  1. Configure logging
  2. Connect to MySQL
  3. Load ML models (once)
  4. Mount API routers
  5. Start background cleanup scheduler
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analysis, api_keys, auth, health, usage, users
from app.config import get_settings
from app.database import close_db, connect_db
from app.utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan — runs startup then shutdown logic."""
    settings = get_settings()
    configure_logging(debug=settings.debug)

    logger.info("=" * 60)
    logger.info("  %s v%s starting …", settings.app_name, settings.app_version)
    logger.info("  Environment : %s", settings.environment)
    logger.info("  Model dir   : %s", settings.model_directory)
    logger.info("=" * 60)

    # ── Database ─────────────────────────────────────────────────────────────
    try:
        await connect_db()
    except Exception as exc:
        logger.error("MySQL connection failed: %s", exc)
        logger.warning("Running WITHOUT database -- most endpoints will fail.")

    # ── ML Models ─────────────────────────────────────────────────────────────
    try:
        from app.ml.model_loader import load_all_models
        load_all_models(settings.model_dir)
    except Exception as exc:
        logger.error("Model loading failed: %s", exc)
        logger.warning("Running WITHOUT ML models — analysis will be limited.")

    # ── Background cleanup task ───────────────────────────────────────────────
    cleanup_task = asyncio.create_task(_background_cleanup(settings.cleanup_interval_hours))

    logger.info("DeepGuard is ready.")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await close_db()
    logger.info("DeepGuard shut down.")


async def _background_cleanup(interval_hours: int) -> None:
    """Periodically delete expired retained images."""
    from app.services.storage_service import cleanup_expired_files
    while True:
        await asyncio.sleep(interval_hours * 3600)
        try:
            deleted = await cleanup_expired_files(retention_days=7)
            if deleted:
                logger.info("Background cleanup: removed %d expired file(s)", deleted)
        except Exception as exc:
            logger.error("Background cleanup error: %s", exc)


# ── Application factory ───────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="DeepGuard API",
        description=(
            "AI-powered deepfake identification platform. Provides probabilistic forensic "
            "analysis combining provenance signals, EXIF metadata forensics, and ML pattern "
            "ensemble detection. Results are NOT definitive proof of authenticity or manipulation."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Security headers middleware ───────────────────────────────────────────
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # ── Global error handler ──────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again.",
                },
            },
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    prefix = "/api/v1"
    app.include_router(health.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(api_keys.router, prefix=prefix)
    app.include_router(analysis.router, prefix=prefix)
    app.include_router(usage.router, prefix=prefix)

    # ── Root endpoint ─────────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "service": "DeepGuard API",
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()
