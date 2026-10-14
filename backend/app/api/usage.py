"""
Usage statistics routes (MySQL).
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, func

from app.database import get_session_factory
from app.orm_models import AnalysisORM, UsageORM
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
    factory = get_session_factory()

    since = datetime.now(timezone.utc) - timedelta(days=days)

    async with factory() as session:
        stmt = (
            select(UsageORM)
            .where(
                UsageORM.user_id == user.id,
                UsageORM.timestamp >= since,
            )
            .order_by(UsageORM.timestamp.desc())
        )
        if api_key_id:
            stmt = stmt.where(UsageORM.api_key_id == api_key_id)

        result = await session.execute(stmt)
        rows = result.scalars().all()

    records = []
    for row in rows:
        records.append({
            "id": str(row.id),
            "user_id": row.user_id,
            "api_key_id": row.api_key_id,
            "request_id": row.request_id,
            "assessment": row.assessment,
            "processing_time_ms": row.processing_time_ms,
            "success": row.success,
            "date": row.date,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
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
    factory = get_session_factory()

    async with factory() as session:
        stmt = select(AnalysisORM).where(
            AnalysisORM.user_id == user.id,
            AnalysisORM.deleted_at.is_(None),
        )
        if assessment:
            stmt = stmt.where(AnalysisORM.assessment == assessment)
        if api_key_id:
            stmt = stmt.where(AnalysisORM.api_key_id == api_key_id)

        # Total count
        count_result = await session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar_one()

        # Paginated results
        stmt = stmt.order_by(AnalysisORM.created_at.desc())
        stmt = stmt.offset((page - 1) * limit).limit(limit)
        result = await session.execute(stmt)
        rows = result.scalars().all()

    items = []
    for row in rows:
        items.append({
            "id": str(row.id),
            "request_id": row.request_id,
            "assessment": row.assessment,
            "assessment_confidence": row.assessment_confidence,
            "processing_time_ms": row.processing_time_ms,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "original_filename": row.original_filename,
            "api_key_id": row.api_key_id,
            "model_version": row.model_version,
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
