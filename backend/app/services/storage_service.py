"""
Storage Service — abstraction layer over local/S3 storage.
Handles image file lifecycle, including immediate deletion.
"""
import logging
import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def _upload_path(file_id: str, ext: str = ".jpg") -> Path:
    settings = get_settings()
    return settings.upload_dir / f"{file_id}{ext}"


async def save_image(raw_bytes: bytes, content_type: str) -> str:
    """
    Save image bytes to configured storage.
    Returns a file_id (UUID). Does NOT store original filename.
    """
    ext_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    ext = ext_map.get(content_type, ".jpg")
    file_id = str(uuid.uuid4())

    settings = get_settings()
    if settings.storage_type == "local":
        path = _upload_path(file_id, ext)
        path.write_bytes(raw_bytes)
        logger.debug("Saved image %s (%d bytes)", file_id, len(raw_bytes))
    else:
        # S3 stub — implement when S3 credentials are configured
        _upload_to_s3(raw_bytes, file_id, ext, settings)

    return file_id


async def delete_image(file_id: str) -> None:
    """Delete an image from storage (any extension)."""
    settings = get_settings()
    if settings.storage_type == "local":
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            path = _upload_path(file_id, ext)
            if path.exists():
                path.unlink(missing_ok=True)
                logger.debug("Deleted image file: %s", path)
                return
    else:
        _delete_from_s3(file_id, settings)


async def delete_image_immediately(file_id: Optional[str]) -> None:
    """Called right after analysis when policy is 'delete_immediately'."""
    if not file_id:
        return
    await delete_image(file_id)
    logger.info("Immediate deletion completed for file_id=%s", file_id)


async def cleanup_expired_files(retention_days: int = 7) -> int:
    """
    Background cleanup: delete files older than retention_days.
    Returns the count of deleted files.
    """
    settings = get_settings()
    if settings.storage_type != "local":
        return 0  # S3 lifecycle policies handle this in production

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    upload_dir = settings.upload_dir
    deleted = 0

    for path in upload_dir.iterdir():
        if path.is_file():
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1

    if deleted:
        logger.info("Cleanup: deleted %d expired file(s)", deleted)
    return deleted


def _upload_to_s3(raw_bytes: bytes, file_id: str, ext: str, settings) -> None:
    """S3 upload stub — implement with boto3 when S3 is configured."""
    raise NotImplementedError("S3 storage not yet configured. Set STORAGE_TYPE=local for development.")


def _delete_from_s3(file_id: str, settings) -> None:
    """S3 delete stub."""
    raise NotImplementedError("S3 storage not yet configured.")
