"""
Request/file validation utilities.
"""
import imghdr
import io
import logging
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Magic bytes / imghdr mappings
ALLOWED_IMGHDR = {"jpeg", "png", "webp"}


async def validate_image_upload(file: UploadFile, max_bytes: int) -> bytes:
    """
    Read and validate an uploaded image file.
    Returns raw bytes if valid; raises HTTPException otherwise.
    """
    # 1. Content-type header check (not trusted alone, but useful)
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_CONTENT_TYPE",
                "message": f"Unsupported content type '{file.content_type}'. Allowed: JPEG, PNG, WEBP.",
            },
        )

    # 2. Extension check
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_EXTENSION",
                    "message": f"Unsupported file extension '{ext}'.",
                },
            )

    # 3. Read bytes
    raw = await file.read()

    # 4. Size check
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"File exceeds maximum size of {max_bytes // (1024 * 1024)} MB.",
            },
        )

    if len(raw) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "EMPTY_FILE", "message": "Uploaded file is empty."},
        )

    # 5. Magic-byte validation — trust file content, not the extension
    detected = imghdr.what(io.BytesIO(raw))
    if detected not in ALLOWED_IMGHDR:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_IMAGE",
                "message": "The uploaded file does not appear to be a valid image.",
            },
        )

    return raw


def safe_filename(original: str | None) -> str:
    """Return a safe original filename for logging (strip path traversal)."""
    if not original:
        return "unknown"
    return Path(original).name[:128]
