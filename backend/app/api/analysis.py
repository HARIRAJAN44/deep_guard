"""
Image Analysis API routes -- the core three-stage pipeline endpoint (in-memory store).
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.db.memory_store import (
    get_api_key_by_id,
    record_usage,
    store_analysis,
    get_analysis,
    list_analyses_for_user,
    soft_delete_analysis,
)
from app.models.analysis import AnalysisResponse
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
        key_row = get_api_key_by_id(api_key_id)
        if key_row:
            monthly = key_row["requests_this_month"]
            limit = key_row["monthly_limit"]
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

    # -- Persist analysis record to in-memory store ---------------------------
    analysis_data = {
        "request_id": analysis.request_id,
        "user_id": user_id,
        "api_key_id": api_key_id,
        "original_filename": analysis.original_filename,
        "file_size_bytes": analysis.file_size_bytes,
        "image_width": analysis.image_width,
        "image_height": analysis.image_height,
        "provenance": analysis.provenance.model_dump() if analysis.provenance else None,
        "metadata": analysis.metadata.model_dump() if analysis.metadata else None,
        "ensemble": analysis.ensemble.model_dump() if analysis.ensemble else None,
        "assessment": analysis.assessment,
        "assessment_confidence": analysis.assessment_confidence,
        "assessment_explanation": analysis.assessment_explanation,
        "assessment_reasons": analysis.assessment_reasons,
        "model_version": analysis.model_version,
        "processing_time_ms": analysis.processing_time_ms,
        "status": analysis.status,
        "error": analysis.error,
        "storage_path": analysis.storage_path,
        "retention_policy": analysis.retention_policy,
        "created_at": analysis.created_at,
        "deleted_at": None,
    }
    store_analysis(analysis.request_id, analysis_data)

    # Usage tracking
    record_usage(
        user_id=user_id,
        api_key_id=api_key_id,
        request_id=analysis.request_id,
        assessment=analysis.assessment,
        processing_time_ms=analysis.processing_time_ms,
        success=success,
    )

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
async def get_analysis_endpoint(
    request_id: str,
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    try:
        user_id, api_key_id, _ = await _resolve_caller(authorization, credentials)
    except HTTPException:
        raise

    row = get_analysis(request_id)

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    # Ownership check
    if row.get("user_id") and row["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    data = {
        "request_id": row.get("request_id"),
        "user_id": row.get("user_id"),
        "api_key_id": row.get("api_key_id"),
        "original_filename": row.get("original_filename"),
        "file_size_bytes": row.get("file_size_bytes"),
        "image_width": row.get("image_width"),
        "image_height": row.get("image_height"),
        "provenance": row.get("provenance"),
        "metadata": row.get("metadata"),
        "ensemble": row.get("ensemble"),
        "assessment": row.get("assessment"),
        "assessment_confidence": row.get("assessment_confidence"),
        "assessment_explanation": row.get("assessment_explanation"),
        "assessment_reasons": row.get("assessment_reasons", []),
        "model_version": row.get("model_version"),
        "processing_time_ms": row.get("processing_time_ms"),
        "status": row.get("status"),
        "storage_path": row.get("storage_path"),
        "retention_policy": row.get("retention_policy"),
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "deleted_at": row.get("deleted_at").isoformat() if row.get("deleted_at") else None,
    }
    return {"success": True, "data": data}


@router.delete(
    "/{request_id}",
    summary="Delete an analysis record",
    description="Marks an analysis as deleted and removes associated image files.",
)
async def delete_analysis_endpoint(
    request_id: str,
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    try:
        user_id, _, _ = await _resolve_caller(authorization, credentials)
    except HTTPException:
        raise

    row = get_analysis(request_id)

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    if row.get("user_id") and row["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Delete image if still retained
    if row.get("storage_path"):
        await delete_image_immediately(row["storage_path"])

    soft_delete_analysis(request_id)

    return {"success": True, "data": {"message": "Analysis record and image deleted."}}