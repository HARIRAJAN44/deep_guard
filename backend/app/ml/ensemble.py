"""
Ensemble runner — runs all available trained models on a preprocessed image
and produces an aggregate result via majority-weighted voting.

Label mapping (from original main.py line 37):
  sigmoid output > 0.5  → leans toward Real
  sigmoid output ≤ 0.5  → leans toward Fake

We call this a "model score" not a "calibrated probability" because the models
are not explicitly probability-calibrated.
"""
import logging
from typing import Optional

import numpy as np

from app.ml.model_loader import ModelRegistry
from app.ml.preprocessing import preprocess_image_bytes
from app.models.analysis import EnsembleResult, ModelScore

logger = logging.getLogger(__name__)


def _score_to_label(score: float) -> str:
    """
    Convert a raw sigmoid output to a human-readable label.
    Original mapping from main.py: pred > 0.5 → Real, else Fake.
    """
    if score > 0.65:
        return "likely_real"
    elif score < 0.35:
        return "likely_fake"
    else:
        return "inconclusive"


def run_ensemble(image_bytes: bytes, registry: ModelRegistry) -> EnsembleResult:
    """
    Run all loaded models on image_bytes and return an EnsembleResult.
    Individual model failures are tolerated — the result still includes
    scores from all successfully-run models.
    """
    if not registry.is_any_available():
        return EnsembleResult(
            models={},
            ensemble_label="inconclusive",
            ensemble_score=0.5,
            models_run=0,
            models_available=0,
            explanation="No ML models are currently available. Analysis is inconclusive.",
        )

    # Preprocess image once — reuse for all models
    try:
        arr = preprocess_image_bytes(image_bytes)
    except Exception as exc:
        logger.error("Image preprocessing failed: %s", exc)
        return EnsembleResult(
            models={},
            ensemble_label="inconclusive",
            ensemble_score=0.5,
            models_run=0,
            models_available=len(registry.all_keys()),
            explanation="Image preprocessing failed — ML analysis could not be completed.",
        )

    model_scores: dict[str, ModelScore] = {}
    raw_scores: list[float] = []
    models_available = 0

    for key in registry.all_keys():
        loaded = registry.get(key)
        if not loaded:
            continue

        models_available += 1

        if loaded.status != "loaded" or loaded.model is None:
            model_scores[key] = ModelScore(
                label="unavailable",
                score=0.5,
                status="unavailable",
            )
            continue

        try:
            prediction = loaded.model.predict(arr, verbose=0)
            # prediction shape: (1, 1) → extract scalar
            raw_score = float(prediction[0][0])
            label = _score_to_label(raw_score)
            model_scores[key] = ModelScore(
                label=label,
                score=round(raw_score, 4),
                status="success",
            )
            raw_scores.append(raw_score)
            logger.debug("  %s → score=%.4f label=%s", loaded.display_name, raw_score, label)
        except Exception as exc:
            logger.error("Model '%s' inference failed: %s", loaded.display_name, exc)
            model_scores[key] = ModelScore(
                label="error",
                score=0.5,
                status="error",
            )

    models_run = len(raw_scores)

    if models_run == 0:
        return EnsembleResult(
            models=model_scores,
            ensemble_label="inconclusive",
            ensemble_score=0.5,
            models_run=0,
            models_available=models_available,
            explanation="All ML models encountered errors during inference.",
        )

    # ── Weighted majority vote ────────────────────────────────────────────────
    # Average of raw sigmoid scores
    avg_score = float(np.mean(raw_scores))
    ensemble_label = _score_to_label(avg_score)

    # Build explanation
    if models_run < models_available:
        caveat = f"Analysis completed with {models_run} of {models_available} ML detectors. "
    else:
        caveat = ""

    real_count = sum(1 for s in raw_scores if s > 0.5)
    fake_count = models_run - real_count

    if ensemble_label == "likely_real":
        verdict_text = f"{real_count} of {models_run} pattern analyzers indicate real-image characteristics."
    elif ensemble_label == "likely_fake":
        verdict_text = f"{fake_count} of {models_run} pattern analyzers indicate manipulated/synthetic image characteristics."
    else:
        verdict_text = f"Pattern analyzers returned mixed or borderline signals ({real_count} real-leaning, {fake_count} fake-leaning)."

    explanation = caveat + verdict_text

    return EnsembleResult(
        models=model_scores,
        ensemble_label=ensemble_label,
        ensemble_score=round(avg_score, 4),
        models_run=models_run,
        models_available=models_available,
        explanation=explanation,
    )
