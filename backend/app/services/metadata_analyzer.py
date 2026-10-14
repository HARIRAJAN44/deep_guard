"""
Stage 2 — Image Metadata / EXIF Forensics.

Extracts and analyses all available metadata from an uploaded image.

IMPORTANT:
  Metadata is EVIDENCE, not PROOF.
  EXIF data can be: removed, modified, copied, or spoofed.
  "Camera metadata present" ≠ "Image is real."
  "No EXIF" ≠ "Image is fake."
"""
import io
import logging
from datetime import datetime
from typing import Any, Optional

from PIL import Image, ExifTags
import piexif

logger = logging.getLogger(__name__)

# EXIF tag IDs we care about
_SOFTWARE_TAG = 0x0131      # Software
_MAKE_TAG = 0x010F          # Camera Make
_MODEL_TAG = 0x0110         # Camera Model
_DATETIME_TAG = 0x0132      # DateTime
_DATETIME_ORIG = 0x9003     # DateTimeOriginal
_GPS_IFD = 0x8825           # GPS IFD

# Software values that suggest AI-generation or editing
_EDITING_HINTS = [
    "photoshop", "lightroom", "gimp", "affinity", "capture one",
    "darktable", "luminar", "topaz", "photomatix", "paintshop",
    "snapseed", "vsco", "facetune", "picsart",
]

_AI_GENERATION_HINTS = [
    "stable diffusion", "midjourney", "dall-e", "openai", "firefly",
    "imagen", "runway", "deepai", "novelai", "automatic1111", "comfyui",
]


def _get_exif_tag(exif_dict: dict, ifd: str, tag_id: int) -> Optional[Any]:
    """Safely retrieve a tag value from a piexif-loaded dict."""
    try:
        ifd_data = exif_dict.get(ifd, {})
        val = ifd_data.get(tag_id)
        if isinstance(val, bytes):
            return val.decode("utf-8", errors="ignore").strip().strip("\x00")
        return val
    except Exception:
        return None


def analyze_metadata(image_bytes: bytes) -> dict[str, Any]:
    """
    Run Stage 2 EXIF / metadata forensics.
    Returns a dict compatible with MetadataResult.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        return {
            "has_exif": False,
            "camera_make": None,
            "camera_model": None,
            "software": None,
            "capture_timestamp": None,
            "gps_present": False,
            "editing_software": None,
            "metadata_integrity": "unknown",
            "explanation": f"Could not open image for metadata analysis: {exc}",
            "raw_fields": {},
        }

    result: dict[str, Any] = {
        "has_exif": False,
        "camera_make": None,
        "camera_model": None,
        "software": None,
        "capture_timestamp": None,
        "gps_present": False,
        "editing_software": None,
        "metadata_integrity": "unknown",
        "explanation": "",
        "raw_fields": {},
    }

    # ── Read EXIF ─────────────────────────────────────────────────────────────
    exif_bytes = img.info.get("exif", b"")
    exif_dict: Optional[dict] = None

    if exif_bytes:
        try:
            exif_dict = piexif.load(exif_bytes)
            result["has_exif"] = True
        except Exception:
            result["has_exif"] = False

    if exif_dict:
        make = _get_exif_tag(exif_dict, "0th", _MAKE_TAG)
        model = _get_exif_tag(exif_dict, "0th", _MODEL_TAG)
        software = _get_exif_tag(exif_dict, "0th", _SOFTWARE_TAG)
        dt_original = _get_exif_tag(exif_dict, "Exif", _DATETIME_ORIG)
        dt_fallback = _get_exif_tag(exif_dict, "0th", _DATETIME_TAG)
        gps_data = exif_dict.get("GPS", {})

        result["camera_make"] = make or None
        result["camera_model"] = model or None
        result["software"] = software or None
        result["capture_timestamp"] = dt_original or dt_fallback or None
        result["gps_present"] = bool(gps_data)

        # Detect editing/AI software
        sw_lower = (software or "").lower()
        for hint in _EDITING_HINTS:
            if hint in sw_lower:
                result["editing_software"] = software
                break
        for hint in _AI_GENERATION_HINTS:
            if hint in sw_lower:
                result["editing_software"] = software
                break

        # Collect interesting raw fields
        raw: dict[str, str] = {}
        if make:
            raw["Make"] = make
        if model:
            raw["Model"] = model
        if software:
            raw["Software"] = software
        if result["capture_timestamp"]:
            raw["DateTimeOriginal"] = result["capture_timestamp"]
        if result["gps_present"]:
            raw["GPS"] = "present"
        result["raw_fields"] = raw

    # ── PNG text chunks (no EXIF in many PNG files) ──────────────────────────
    png_text = getattr(img, "text", {})
    if png_text and not result["has_exif"]:
        result["has_exif"] = True  # treat PNG chunks as "metadata present"
        for k, v in png_text.items():
            if k.lower() in ("software", "comment", "author", "description", "create-date"):
                result["raw_fields"][k] = v[:200]

    # ── Integrity assessment & explanation ────────────────────────────────────
    if not result["has_exif"]:
        result["metadata_integrity"] = "missing"
        result["explanation"] = (
            "No EXIF or embedded metadata was detected. This is common for images that have been "
            "screenshot, re-encoded, stripped, or published through a platform that removes metadata. "
            "Absence of metadata does not indicate manipulation."
        )
    elif result["camera_make"] and result["capture_timestamp"] and not result["editing_software"]:
        result["metadata_integrity"] = "consistent"
        result["explanation"] = (
            f"Camera metadata is present and appears internally consistent "
            f"(Make: {result['camera_make']}, Model: {result['camera_model']}, "
            f"Timestamp: {result['capture_timestamp']}). "
            "However, EXIF data can be copied or spoofed, so this cannot be treated as proof of authenticity."
        )
    elif result["editing_software"]:
        result["metadata_integrity"] = "inconsistent"
        sw = result["editing_software"]
        is_ai = any(h in sw.lower() for h in _AI_GENERATION_HINTS)
        if is_ai:
            result["explanation"] = (
                f"The 'Software' field contains a value associated with AI image generation: '{sw}'. "
                "This may indicate the image was created or processed by an AI tool."
            )
        else:
            result["explanation"] = (
                f"The 'Software' field indicates image editing software was used: '{sw}'. "
                "This does not necessarily mean the image is fake — many authentic photos are post-processed."
            )
    else:
        result["metadata_integrity"] = "partial"
        result["explanation"] = (
            "Some metadata is present but key fields (camera make/model or timestamp) are missing. "
            "This can occur with images from certain devices, apps, or after partial metadata stripping."
        )

    return result
