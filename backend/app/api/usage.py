"""
Usage statistics routes (in-memory store).
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.memory_store import get_usage_for_user, list_analyses_for_user
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/usage", tags=["Usage"])
security = HTTPBearer()


@router.get(
    "/",
    summary="Get usage statistics",
    description="Returns aggregate usage stats for the authenticated user.",
)
async def get_usage(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    api_key_id: Optional[str] = Query(None, description="Filter by API key ID"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    user = await get_current_user(credentials.credentials)

    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = get_usage_for_user(user.id, since, api_key_id)

    records = []
    for row in rows:
        records.append({
            "id": row.get("id"),
            "user_id": row.get("user_id"),
            "api_key_id": row.get("api_key_id"),
            "request_id": row.get("request_id"),
            "assessment": row.get("assessment"),
            "processing_time_ms": row.get("processing_time_ms"),
            "success": row.get("success"),
            "date": row.get("date"),
            "timestamp": row.get("timestamp").isoformat() if row.get("timestamp") else None,
        })

    # Aggregate
    total = len(records)
    successful = sum(1 for r in records if r.get("success"))
    failed = total - successful
    by_assessment: dict = {}
    by_day: dict = {}

    for r in records:
        a = r.get("assessment", "unknown")
        by_assessment[a] = by_assessment.get(a, 0) + 1

        day = r.get("date", "")
        if day:
            by_day[day] = by_day.get(day, 0) + 1

    daily_series = [{"date": d, "count": c} for d, c in sorted(by_day.items())]

    return {
        "success": True,
        "data": {
            "period_days": days,
            "total_requests": total,
            "successful": successful,
            "failed": failed,
            "by_assessment": by_assessment,
            "daily_series": daily_series,
        },
    }


@router.get(
    "/history",
    summary="Get analysis history",
    description="Paginated list of analysis results.",
)
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    assessment: Optional[str] = Query(None),
    api_key_id: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    user = await get_current_user(credentials.credentials)

    rows = list_analyses_for_user(user.id, assessment, api_key_id)

    # Total count
    total = len(rows)

    # Paginated results
    start = (page - 1) * limit
    end = start + limit
    paginated = rows[start:end]

    items = []
    for row in paginated:
        items.append({
            "request_id": row.get("request_id"),
            "assessment": row.get("assessment"),
            "assessment_confidence": row.get("assessment_confidence"),
            "processing_time_ms": row.get("processing_time_ms"),
            "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
            "original_filename": row.get("original_filename"),
            "api_key_id": row.get("api_key_id"),
            "model_version": row.get("model_version"),
        })

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        },
    }