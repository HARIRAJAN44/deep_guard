"""
Analysis document Pydantic model (MySQL-backed).
"""
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# -- Sub-models for the three-stage pipeline ----------------------------------

class ProvenanceResult(BaseModel):
    status: str                     # indicator_found | no_indicator_found | error
    provider: Optional[str] = None
    indicator_type: Optional[str] = None
    confidence: float = 0.0
    explanation: str = ""
    details: dict = Field(default_factory=dict)


class MetadataResult(BaseModel):
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    software: Optional[str] = None
    capture_timestamp: Optional[str] = None
    gps_present: bool = False
    editing_software: Optional[str] = None
    has_exif: bool = False
    metadata_integrity: str = "unknown"   # consistent | inconsistent | missing | unknown
    explanation: str = ""
    raw_fields: dict = Field(default_factory=dict)


class ModelScore(BaseModel):
    label: str                      # likely_real | likely_fake | inconclusive
    score: float                    # raw sigmoid output [0..1]
    status: str = "success"         # success | error | unavailable


class EnsembleResult(BaseModel):
    models: dict[str, ModelScore] = Field(default_factory=dict)
    ensemble_label: str = "inconclusive"
    ensemble_score: float = 0.5
    models_run: int = 0
    models_available: int = 0
    explanation: str = ""


class AnalysisDocument(BaseModel):
    id: Optional[int] = None
    request_id: str                                 # UUID
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    # File info (sanitised -- no original path stored)
    original_filename: Optional[str] = None         # basename only, for display
    file_size_bytes: int = 0
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    # Three-stage results
    provenance: Optional[ProvenanceResult] = None
    metadata: Optional[MetadataResult] = None
    ensemble: Optional[EnsembleResult] = None
    # Final verdict
    assessment: str = "inconclusive"               # likely_authentic | likely_ai_generated | likely_manipulated | suspicious | inconclusive
    assessment_confidence: float = 0.0
    assessment_explanation: str = ""
    assessment_reasons: list[str] = Field(default_factory=list)
    # ML versioning
    model_version: str = "v1"
    # Processing
    processing_time_ms: int = 0
    status: str = "completed"                      # completed | failed | processing
    error: Optional[str] = None
    # Storage / privacy
    storage_path: Optional[str] = None             # None if deleted immediately
    retention_policy: str = "delete_immediately"
    # Lifecycle
    created_at: datetime = Field(default_factory=utcnow)
    deleted_at: Optional[datetime] = None          # set when image/result purged

    class Config:
        from_attributes = True
        protected_namespaces = ()


class AnalysisResponse(BaseModel):
    """Public API response envelope for an analysis result."""

    class Config:
        protected_namespaces = ()

    request_id: str
    status: str
    assessment: str
    assessment_confidence: float
    assessment_explanation: str
    assessment_reasons: list[str]
    stages: dict[str, Any]
    model_version: str
    processing_time_ms: int
    created_at: datetime
