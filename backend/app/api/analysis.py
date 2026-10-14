"""
Image Analysis API routes -- the core three-stage pipeline endpoint (MySQL).
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update

from app.config import get_settings
from app.database import get_session_factory
from app.models.analysis import AnalysisResponse
from app.orm_models import AnalysisORM, APIKeyORM, UsageORM
from app.services.analysis_service import run_full_analysis
from app.services.api_key_service import authenticate_api_key, record_api_key_result
from app.services.auth_service import get_current_user
from app.services.storage_service import delete_image_immediately, save_image
from app.utils.validators import safe_filename, validate_image_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Analysis"])
security = HTTPBearer(auto_error=False)


async def _resolve_caller(
    authorization: Optional[str],
    credentials: Optional[HTTPAuthorizationCredentials],
) -> tuple[Optional[str], Optional[str], str]:
    """
    Determine who is calling:
      - Bearer JWT  -> web user
      - Bearer dg_* -> API customer
    Returns (user_id, api_key_id, retention_policy).
    """
    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
    elif credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Authentication required."},
        )

    if token.startswith("dg_"):
        # API key auth
        key_doc = await authenticate_api_key(token)
        policy = key_doc.get("privacy_policy", {})
        retention = policy.get("retention", "delete_immediately")
        return key_doc.get("user_id"), str(key_doc["_id"]), retention
    else:
        # JWT auth -- default to immediate deletion for web UI users
        user = await get_current_user(token)
        return user.id, None, "delete_immediately"


@router.post(
    "/image",
    summary="Analyse an image for deepfake indicators",
    description=(
        "Submits an image through the three-stage forensic pipeline: "
        "provenance analysis, EXIF/metadata forensics, and ML pattern ensemble. "
        "Returns a probabilistic forensic assessment. "
        "Results are NOT definitive proof of authenticity or manipulation."
    ),
)
async def analyze_image(
    file: UploadFile = File(..., description="JPEG, PNG, or WEBP image file"),
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    settings = get_settings()
    request_id = str(uuid.uuid4())

    # -- Auth resolution ------------------------------------------------------
    try:
        user_id, api_key_id, retention_policy = await _resolve_caller(authorization, credentials)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    # -- Rate limit check (basic per-key counter) -----------------------------
    if api_key_id:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(APIKeyORM).where(APIKeyORM.id == int(api_key_id))
            )
            key_row = result.scalar_one_or_none()
            if key_row:
                monthly = key_row.requests_this_month
                limit = key_row.monthly_limit
                if monthly >= limit:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Monthly request limit ({limit}) reached.",
                        },
                        headers={"X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": "0"},
                    )

    # -- File validation ------------------------------------------------------
    try:
        raw_bytes = await validate_image_upload(file, settings.max_upload_bytes)
    except HTTPException:
        if api_key_id:
            await record_api_key_result(api_key_id, success=False)
        raise

    original_name = safe_filename(file.filename)
    content_type = file.content_type or "image/jpeg"

    # -- Save (only if retention is not immediate delete) ---------------------
    file_id: Optional[str] = None
    if retention_policy != "delete_immediately":
        try:
            file_id = await save_image(raw_bytes, content_type)
        except Exception as exc:
            logger.warning("Image save failed (will proceed without storage): %s", exc)

    # -- Run the three-stage pipeline -----------------------------------------
    try:
        analysis = await run_full_analysis(
            image_bytes=raw_bytes,
            original_filename=original_name,
            user_id=user_id,
            api_key_id=api_key_id,
            retention_policy=retention_policy,
            model_version=settings.model_version,
        )
        analysis.storage_path = file_id
        success = True
    except Exception as exc:
        logger.error("Analysis pipeline error request_id=%s: %s", request_id, exc, exc_info=True)
        if api_key_id:
            await record_api_key_result(api_key_id, success=False)
        if file_id:
            await delete_image_immediately(file_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "ANALYSIS_FAILED", "message": "Analysis could not be completed."},
        )

    # -- Immediate deletion ---------------------------------------------------
    if retention_policy == "delete_immediately" and file_id:
        await delete_image_immediately(file_id)
        analysis.storage_path = None

    # -- Persist analysis record to MySQL -------------------------------------
    factory = get_session_factory()
    async with factory() as session:
        session.add(AnalysisORM(
            request_id=analysis.request_id,
            user_id=user_id,
            api_key_id=api_key_id,
            original_filename=analysis.original_filename,
            file_size_bytes=analysis.file_size_bytes,
            image_width=analysis.image_width,
            image_height=analysis.image_height,
            provenance_json=analysis.provenance.model_dump_json() if analysis.provenance else None,
            metadata_json=analysis.metadata.model_dump_json() if analysis.metadata else None,
            ensemble_json=analysis.ensemble.model_dump_json() if analysis.ensemble else None,
            assessment=analysis.assessment,
            assessment_confidence=analysis.assessment_confidence,
            assessment_explanation=analysis.assessment_explanation,
            assessment_reasons_json=json.dumps(analysis.assessment_reasons),
            model_version=analysis.model_version,
            processing_time_ms=analysis.processing_time_ms,
            status=analysis.status,
            error=analysis.error,
            storage_path=analysis.storage_path,
            retention_policy=analysis.retention_policy,
            created_at=analysis.created_at,
        ))

        # Usage tracking
        session.add(UsageORM(
            user_id=user_id,
            api_key_id=api_key_id,
            request_id=analysis.request_id,
            assessment=analysis.assessment,
            processing_time_ms=analysis.processing_time_ms,
            success=success,
            date=datetime.now(timezone.utc).date().isoformat(),
            timestamp=datetime.now(timezone.utc),
        ))
        await session.commit()

    if api_key_id:
        await record_api_key_result(api_key_id, success=True)

    # -- Build response -------------------------------------------------------
    response_data = {
        "request_id": analysis.request_id,
        "status": analysis.status,
        "assessment": analysis.assessment,
        "assessment_confidence": analysis.assessment_confidence,
        "assessment_explanation": analysis.assessment_explanation,
        "assessment_reasons": analysis.assessment_reasons,
        "stages": {
            "provenance": analysis.provenance.model_dump() if analysis.provenance else None,
            "metadata": analysis.metadata.model_dump() if analysis.metadata else None,
            "ensemble": analysis.ensemble.model_dump() if analysis.ensemble else None,
        },
        "model_version": analysis.model_version,
        "processing_time_ms": analysis.processing_time_ms,
        "created_at": analysis.created_at.isoformat(),
    }

    return {"success": True, "data": response_data, "request_id": analysis.request_id}


@router.get(
    "/{request_id}",
    summary="Retrieve a previous analysis result",
    description="Fetch a stored analysis by request ID. Subject to retention policy.",
)
async def get_analysis(
    request_id: str,
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    try:
        user_id, api_key_id, _ = await _resolve_caller(authorization, credentials)
    except HTTPException:
        raise

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AnalysisORM).where(AnalysisORM.request_id == request_id)
        )
        row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    # Ownership check
    if row.user_id and row.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    data = {
        "id": str(row.id),
        "request_id": row.request_id,
        "user_id": row.user_id,
        "api_key_id": row.api_key_id,
        "original_filename": row.original_filename,
        "file_size_bytes": row.file_size_bytes,
        "image_width": row.image_width,
        "image_height": row.image_height,
        "provenance": json.loads(row.provenance_json) if row.provenance_json else None,
        "metadata": json.loads(row.metadata_json) if row.metadata_json else None,
        "ensemble": json.loads(row.ensemble_json) if row.ensemble_json else None,
        "assessment": row.assessment,
        "assessment_confidence": row.assessment_confidence,
        "assessment_explanation": row.assessment_explanation,
        "assessment_reasons": json.loads(row.assessment_reasons_json) if row.assessment_reasons_json else [],
        "model_version": row.model_version,
        "processing_time_ms": row.processing_time_ms,
        "status": row.status,
        "storage_path": row.storage_path,
        "retention_policy": row.retention_policy,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "deleted_at": row.deleted_at.isoformat() if row.deleted_at else None,
    }
    return {"success": True, "data": data}


@router.delete(
    "/{request_id}",
    summary="Delete an analysis record",
    description="Marks an analysis as deleted and removes associated image files.",
)
async def delete_analysis(
    request_id: str,
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    try:
        user_id, _, _ = await _resolve_caller(authorization, credentials)
    except HTTPException:
        raise

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AnalysisORM).where(AnalysisORM.request_id == request_id)
        )
        row = result.scalar_one_or_none()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

        if row.user_id and row.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Delete image if still retained
        if row.storage_path:
            await delete_image_immediately(row.storage_path)

        await session.execute(
            update(AnalysisORM)
            .where(AnalysisORM.request_id == request_id)
            .values(deleted_at=datetime.now(timezone.utc), storage_path=None)
        )
        await session.commit()

    return {"success": True, "data": {"message": "Analysis record and image deleted."}}
