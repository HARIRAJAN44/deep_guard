"""
User profile routes (in-memory store).
"""
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.memory_store import list_analyses_for_user
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])
security = HTTPBearer()


@router.get(
    "/me",
    summary="Get user profile",
)
async def get_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(credentials.credentials)
    return {"success": True, "data": user.model_dump()}


@router.get(
    "/me/stats",
    summary="Get user analysis statistics",
)
async def get_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(credentials.credentials)

    # Get all analyses for this user
    rows = list_analyses_for_user(user.id)

    # Total analyses
    total = len(rows)

    # Assessment breakdown
    assessments = {}
    for label in ["likely_authentic", "likely_ai_generated", "likely_manipulated", "suspicious", "inconclusive"]:
        assessments[label] = sum(1 for r in rows if r.get("assessment") == label)

    # Recent analyses (last 10)
    recent = []
    for row in rows[:10]:
        recent.append({
            "request_id": row.get("request_id"),
            "assessment": row.get("assessment"),
            "assessment_confidence": row.get("assessment_confidence"),
            "processing_time_ms": row.get("processing_time_ms"),
            "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
            "original_filename": row.get("original_filename"),
        })

    return {
        "success": True,
        "data": {
            "total_analyses": total,
            "assessments": assessments,
            "recent_analyses": recent,
        },
    }