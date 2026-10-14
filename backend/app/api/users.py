"""
User profile routes (MySQL).
"""
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, func

from app.database import get_session_factory
from app.orm_models import AnalysisORM
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
    factory = get_session_factory()

    async with factory() as session:
        # Total analyses
        total_result = await session.execute(
            select(func.count()).where(
                AnalysisORM.user_id == user.id,
                AnalysisORM.deleted_at.is_(None),
            )
        )
        total = total_result.scalar_one()

        # Assessment breakdown
        assessments = {}
        for label in ["likely_authentic", "likely_ai_generated", "likely_manipulated", "suspicious", "inconclusive"]:
            count_result = await session.execute(
                select(func.count()).where(
                    AnalysisORM.user_id == user.id,
                    AnalysisORM.assessment == label,
                    AnalysisORM.deleted_at.is_(None),
                )
            )
            assessments[label] = count_result.scalar_one()

        # Recent analyses (last 10)
        recent_result = await session.execute(
            select(AnalysisORM)
            .where(
                AnalysisORM.user_id == user.id,
                AnalysisORM.deleted_at.is_(None),
            )
            .order_by(AnalysisORM.created_at.desc())
            .limit(10)
        )
        recent_rows = recent_result.scalars().all()

    recent = [
        {
            "id": str(row.id),
            "request_id": row.request_id,
            "assessment": row.assessment,
            "assessment_confidence": row.assessment_confidence,
            "processing_time_ms": row.processing_time_ms,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "original_filename": row.original_filename,
        }
        for row in recent_rows
    ]

    return {
        "success": True,
        "data": {
            "total_analyses": total,
            "assessments": assessments,
            "recent_analyses": recent,
        },
    }
