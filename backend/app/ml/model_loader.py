"""
ML Model Loader — loads all 5 existing trained .h5 models ONCE at startup.

IMPORTANT: These models are trained binary classifiers on a real/fake face
dataset. sigmoid output > 0.5 → leans toward Real; ≤ 0.5 → leans toward Fake.
The models are NOT specialised domain algorithms. They are labelled honestly.
"""
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Model registry ────────────────────────────────────────────────────────────
# Maps logical names to .h5 filenames in the model directory.
# Display names are intentionally honest — these are binary classifiers, not
# specialised domain detectors.

MODEL_REGISTRY: list[dict] = [
    {
        "key": "color_pattern",
        "filename": "color_mismatch_model.h5",
        "display_name": "Color-Pattern Analyzer",
        "description": (
            "A binary classifier trained to distinguish real from fake face images "
            "based on colour-related visual patterns."
        ),
    },
    {
        "key": "facial_pattern",
        "filename": "face_shape_model.h5",
        "display_name": "Facial-Pattern Analyzer",
        "description": (
            "A binary classifier trained to distinguish real from fake face images "
            "based on facial structure patterns."
        ),
    },
    {
        "key": "texture_pattern",
        "filename": "texture_analysis_model.h5",
        "display_name": "Texture-Pattern Analyzer",
        "description": (
            "A binary classifier trained to distinguish real from fake face images "
            "based on texture-level patterns."
        ),
    },
    {
        "key": "temporal_feature",
        "filename": "eye_blink_model.h5",
        "display_name": "Temporal-Feature Analyzer",
        "description": (
            "A binary classifier with an LSTM layer trained on still images from a "
            "real/fake face dataset. Note: despite the LSTM, this model operates on "
            "single static images — it does not perform true video-temporal blink detection."
        ),
    },
    {
        "key": "artifact_pattern",
        "filename": "artifact_model.h5",
        "display_name": "Artifact-Pattern Analyzer",
        "description": (
            "A binary classifier trained to distinguish real from fake face images "
            "based on visual artefact patterns."
        ),
    },
]


@dataclass
class LoadedModel:
    key: str
    display_name: str
    description: str
    model: Any  # tf.keras.Model
    input_shape: tuple
    status: str = "loaded"          # loaded | error


@dataclass
class ModelRegistry:
    models: dict[str, LoadedModel] = field(default_factory=dict)
    version: str = "v1"

    def get(self, key: str) -> Optional[LoadedModel]:
        return self.models.get(key)

    def all_keys(self) -> list[str]:
        return list(self.models.keys())

    def health(self) -> dict:
        return {k: v.status for k, v in self.models.items()}

    def is_any_available(self) -> bool:
        return any(m.status == "loaded" for m in self.models.values())


# ── Singleton registry ────────────────────────────────────────────────────────
_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    if _registry is None:
        raise RuntimeError("Models not loaded — call load_all_models() first.")
    return _registry


def load_all_models(model_directory: str | Path) -> ModelRegistry:
    """
    Load every model in MODEL_REGISTRY from model_directory.
    Called ONCE at FastAPI startup. Non-blocking failures are tolerated.
    """
    global _registry

    # Defer heavy TensorFlow import to keep startup fast if TF isn't installed yet
    try:
        import tensorflow as tf
        tf.get_logger().setLevel("ERROR")
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    except ImportError as exc:
        logger.error("TensorFlow not installed: %s", exc)
        _registry = ModelRegistry(models={}, version="v1")
        return _registry

    model_dir = Path(model_directory)
    loaded: dict[str, LoadedModel] = {}

    for spec in MODEL_REGISTRY:
        key = spec["key"]
        path = model_dir / spec["filename"]

        if not path.exists():
            logger.warning("Model file not found: %s — skipping.", path)
            continue

        try:
            logger.info("Loading model '%s' from %s …", spec["display_name"], path)
            keras_model = tf.keras.models.load_model(str(path), compile=False)
            input_shape = tuple(keras_model.input_shape)
            logger.info(
                "  ✓ '%s' loaded — input shape: %s", spec["display_name"], input_shape
            )
            loaded[key] = LoadedModel(
                key=key,
                display_name=spec["display_name"],
                description=spec["description"],
                model=keras_model,
                input_shape=input_shape,
                status="loaded",
            )
        except Exception as exc:
            logger.error("Failed to load model '%s': %s", spec["display_name"], exc)
            # We still register it so the health endpoint shows the failure
            loaded[key] = LoadedModel(
                key=key,
                display_name=spec["display_name"],
                description=spec["description"],
                model=None,
                input_shape=(None, 224, 224, 3),
                status="error",
            )

    _registry = ModelRegistry(models=loaded, version="v1")
    n_ok = sum(1 for m in loaded.values() if m.status == "loaded")
    logger.info("Model loading complete — %d/%d models available.", n_ok, len(loaded))
    return _registry
