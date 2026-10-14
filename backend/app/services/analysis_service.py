"""
Analysis Service — orchestrates the three-stage pipeline and performs
evidence fusion to produce the final assessment.

Pipeline:
  IMAGE → Stage 1 (Provenance) → Stage 2 (Metadata) → Stage 3 (ML Ensemble)
        → Evidence Fusion → Final Assessment
"""
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.ml.ensemble import run_ensemble
from app.ml.model_loader import get_registry
from app.models.analysis import (
    AnalysisDocument,
    EnsembleResult,
    MetadataResult,
    ProvenanceResult,
)
from app.ml.preprocessing import get_image_dimensions
from app.services.metadata_analyzer import analyze_metadata
from app.services.signature_detector import detect_provenance

logger = logging.getLogger(__name__)


# ── Evidence fusion weights ───────────────────────────────────────────────────
# Provenance (30%) + ML ensemble (60%) + Metadata (10%)
W_PROVENANCE = 0.30
W_ENSEMBLE = 0.60
W_METADATA = 0.10


def _fuse_evidence(
    provenance: ProvenanceResult,
    metadata: MetadataResult,
    ensemble: EnsembleResult,
) -> tuple[str, float, str, list[str]]:
    """
    Combine all three stage results into a final assessment.
    Returns (assessment_label, confidence, explanation, reasons_list).
    """
    reasons: list[str] = []
    fake_signal = 0.0        # 0–1, higher = more evidence of manipulation/AI
    real_signal = 0.0        # 0–1, higher = more evidence of authenticity

    # ── Stage 1 provenance ──────────────────────────────────────────────────
    prov_weight = 0.0
    if provenance.status == "indicator_found":
        fake_signal += W_PROVENANCE * provenance.confidence
        prov_weight = provenance.confidence
        reasons.append(
            f"A provenance indicator associated with '{provenance.provider}' was detected "
            f"(confidence: {int(provenance.confidence * 100)}%)."
        )
    elif provenance.status == "no_indicator_found":
        # Absence of provenance is weak real-signal
        real_signal += W_PROVENANCE * 0.2
        reasons.append("No AI-generation provenance indicator was detected in metadata.")

    # ── Stage 2 metadata ────────────────────────────────────────────────────
    if metadata.editing_software:
        sw = metadata.editing_software
        is_ai_sw = any(
            h in sw.lower()
            for h in ["stable diffusion", "midjourney", "dall-e", "openai", "firefly", "imagen"]
        )
        if is_ai_sw:
            fake_signal += W_METADATA * 0.9
            reasons.append(f"Metadata 'Software' field references an AI image tool: '{sw}'.")
        else:
            fake_signal += W_METADATA * 0.3
            reasons.append(f"Metadata indicates image editing software was used: '{sw}'.")
    elif metadata.metadata_integrity == "consistent":
        real_signal += W_METADATA * 0.5
        reasons.append(
            f"Metadata appears consistent with a camera-originated image "
            f"({metadata.camera_make} {metadata.camera_model})."
        )
    elif metadata.metadata_integrity == "missing":
        # Neutral — doesn't push either direction strongly
        reasons.append("No image metadata was detected (common for shared/re-encoded images).")

    # ── Stage 3 ML ensemble ─────────────────────────────────────────────────
    if ensemble.models_run > 0:
        # ensemble_score: > 0.5 → real-leaning, < 0.5 → fake-leaning
        ens = ensemble.ensemble_score
        if ens > 0.5:
            real_signal += W_ENSEMBLE * (ens - 0.5) * 2   # scale to 0–1
        else:
            fake_signal += W_ENSEMBLE * (0.5 - ens) * 2

        if ensemble.ensemble_label == "likely_fake":
            reasons.append(
                f"The ML ensemble ({ensemble.models_run} pattern analyzers) indicates "
                f"manipulated or synthetic image characteristics (ensemble score: {round(ensemble.ensemble_score, 2)})."
            )
        elif ensemble.ensemble_label == "likely_real":
            reasons.append(
                f"The ML ensemble ({ensemble.models_run} pattern analyzers) indicates "
                f"characteristics consistent with real images (ensemble score: {round(ensemble.ensemble_score, 2)})."
            )
        else:
            reasons.append(
                f"The ML ensemble returned mixed or borderline signals "
                f"(ensemble score: {round(ensemble.ensemble_score, 2)})."
            )
    else:
        reasons.append("ML analysis was unavailable — no pattern analyzers ran successfully.")

    # ── Final decision ───────────────────────────────────────────────────────
    net = fake_signal - real_signal           # positive → fake, negative → real
    total_signal = fake_signal + real_signal

    # Map net signal to assessment categories
    if net > 0.35:
        # Strong fake/manipulation evidence
        if provenance.status == "indicator_found" and ensemble.ensemble_label == "likely_fake":
            assessment = "likely_ai_generated"
        elif ensemble.ensemble_label == "likely_fake":
            assessment = "likely_manipulated"
        else:
            assessment = "suspicious"
        confidence = min(0.95, 0.50 + net)
    elif net < -0.25:
        assessment = "likely_authentic"
        confidence = min(0.90, 0.50 + abs(net))
    elif abs(net) < 0.10:
        assessment = "inconclusive"
        confidence = 0.50
    else:
        assessment = "suspicious"
        confidence = 0.50 + abs(net) * 0.5

    # Construct explanation paragraph
    assessment_labels = {
        "likely_ai_generated": "LIKELY AI-GENERATED",
        "likely_manipulated": "LIKELY MANIPULATED",
        "likely_authentic": "LIKELY AUTHENTIC",
        "suspicious": "SUSPICIOUS",
        "inconclusive": "INCONCLUSIVE",
    }
    label_str = assessment_labels.get(assessment, assessment.upper())
    explanation = (
        f"Based on multi-stage forensic analysis, this image is assessed as: {label_str} "
        f"(confidence: {int(confidence * 100)}%). "
        "DeepGuard provides probabilistic forensic indicators — results should not be treated as "
        "definitive proof of authenticity or manipulation."
    )

    return assessment, round(confidence, 3), explanation, reasons


async def run_full_analysis(
    image_bytes: bytes,
    original_filename: Optional[str],
    user_id: Optional[str],
    api_key_id: Optional[str],
    retention_policy: str,
    model_version: str,
) -> AnalysisDocument:
    """
    Execute the complete three-stage pipeline and return an AnalysisDocument.
    """
    request_id = str(uuid.uuid4())
    start_ms = time.monotonic()

    logger.info("Analysis started — request_id=%s", request_id)

    # ── Image dimensions ─────────────────────────────────────────────────────
    try:
        width, height = get_image_dimensions(image_bytes)
    except Exception:
        width, height = None, None

    # ── Stage 1 — Provenance ─────────────────────────────────────────────────
    logger.debug("Stage 1: provenance detection …")
    prov_raw = detect_provenance(image_bytes)
    provenance = ProvenanceResult(**prov_raw)

    # ── Stage 2 — Metadata ───────────────────────────────────────────────────
    logger.debug("Stage 2: metadata analysis …")
    meta_raw = analyze_metadata(image_bytes)
    metadata = MetadataResult(**meta_raw)

    # ── Stage 3 — ML Ensemble ────────────────────────────────────────────────
    logger.debug("Stage 3: ML ensemble …")
    try:
        registry = get_registry()
        ensemble = run_ensemble(image_bytes, registry)
    except RuntimeError:
        # Models not loaded (e.g., TF not installed)
        ensemble = EnsembleResult(
            models={},
            ensemble_label="inconclusive",
            ensemble_score=0.5,
            models_run=0,
            models_available=0,
            explanation="ML models are not available.",
        )

    # ── Evidence Fusion ───────────────────────────────────────────────────────
    assessment, confidence, explanation, reasons = _fuse_evidence(
        provenance, metadata, ensemble
    )

    elapsed_ms = int((time.monotonic() - start_ms) * 1000)
    logger.info(
        "Analysis complete — request_id=%s assessment=%s confidence=%.2f elapsed=%dms",
        request_id, assessment, confidence, elapsed_ms,
    )

    return AnalysisDocument(
        request_id=request_id,
        user_id=user_id,
        api_key_id=api_key_id,
        original_filename=original_filename,
        file_size_bytes=len(image_bytes),
        image_width=width,
        image_height=height,
        provenance=provenance,
        metadata=metadata,
        ensemble=ensemble,
        assessment=assessment,
        assessment_confidence=confidence,
        assessment_explanation=explanation,
        assessment_reasons=reasons,
        model_version=model_version,
        processing_time_ms=elapsed_ms,
        status="completed",
        retention_policy=retention_policy,
        created_at=datetime.now(timezone.utc),
    )
