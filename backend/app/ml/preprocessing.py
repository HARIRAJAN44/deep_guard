"""
Image preprocessing — exactly matching training-time preprocessing.

Training scripts used:
  cv2.resize(img, (224, 224))
  img / 255.0
  np.expand_dims(img, axis=0)

We replicate that here using Pillow + NumPy (no cv2 dependency at runtime).
"""
import io
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

IMG_SIZE = (224, 224)


def preprocess_image_bytes(raw: bytes) -> np.ndarray:
    """
    Convert raw image bytes → model-ready numpy array (1, 224, 224, 3).
    Replicates exactly the preprocessing used during training:
      - Resize to 224×224
      - Convert to RGB
      - Normalise pixel values to [0, 1]
      - Add batch dimension

    Returns ndarray of shape (1, 224, 224, 3) and dtype float32.
    """
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img = img.resize(IMG_SIZE, Image.BILINEAR)
    arr = np.array(img, dtype=np.float32) / 255.0          # (224, 224, 3)
    arr = np.expand_dims(arr, axis=0)                       # (1, 224, 224, 3)
    return arr


def get_image_dimensions(raw: bytes) -> tuple[int, int]:
    """Returns (width, height) of the original image."""
    img = Image.open(io.BytesIO(raw))
    return img.size  # (width, height)
