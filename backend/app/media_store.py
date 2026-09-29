"""
backend/app/media_store.py – Media storage abstraction.

Provides one public function:
    save_upload(file_bytes, filename, content_type) -> url: str

Strategy (auto-selected at startup):
  1. MinIO – if MINIO_ENDPOINT env-var is set and MinIO is reachable.
  2. Local folder – stores to MEDIA_LOCAL_DIR (default: ./media_uploads).

URLs returned:
  • MinIO  → http://<endpoint>/<bucket>/<object_key>
  • Local  → /media/<filename>  (served by FastAPI StaticFiles at /media)

The route POST /api/media wraps this function with validation.
"""

from __future__ import annotations

import hashlib
import io
import logging
import mimetypes
import os
import re
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Configuration from environment variables ──────────────────────────────────

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "")          # e.g. "localhost:9000"
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "wx-media")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

MEDIA_LOCAL_DIR = Path(os.getenv("MEDIA_LOCAL_DIR", "./media_uploads"))

# ── Allowed MIME types ────────────────────────────────────────────────────────

ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif",
    "image/webp", "image/bmp", "image/tiff",
}
ALLOWED_VIDEO_TYPES = {
    "video/mp4", "video/mpeg", "video/webm", "video/quicktime",
    "video/x-msvideo", "video/3gpp",
}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# ── MinIO client (lazy-init) ──────────────────────────────────────────────────

_minio_client = None
_use_minio: bool | None = None   # None = not yet probed


def _get_minio():
    """Return a (client, bucket) tuple, or (None, None) if MinIO is unavailable."""
    global _minio_client, _use_minio

    if _use_minio is False:
        return None, None
    if _use_minio is True and _minio_client is not None:
        return _minio_client, MINIO_BUCKET

    if not MINIO_ENDPOINT:
        _use_minio = False
        logger.info("MediaStore: MINIO_ENDPOINT not set → using local storage.")
        return None, None

    try:
        from minio import Minio
        from minio.error import S3Error

        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        # Ensure bucket exists
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            logger.info("MediaStore: Created MinIO bucket '%s'.", MINIO_BUCKET)
            # Set public read policy on bucket so uploaded media can be viewed by browsers
            try:
                import json
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{MINIO_BUCKET}/*"],
                        }
                    ],
                }
                client.set_bucket_policy(MINIO_BUCKET, json.dumps(policy))
            except Exception as pe:
                logger.debug("MediaStore: Non-fatal error setting bucket policy: %s", pe)

        _minio_client = client
        _use_minio = True
        logger.info("MediaStore: Using MinIO at %s (bucket: %s).", MINIO_ENDPOINT, MINIO_BUCKET)
        return _minio_client, MINIO_BUCKET

    except Exception as exc:
        _use_minio = False
        logger.warning("MediaStore: MinIO unavailable (%s) → using local storage.", exc)
        return None, None


# ── Local fallback ────────────────────────────────────────────────────────────

def _ensure_local_dir() -> Path:
    MEDIA_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    return MEDIA_LOCAL_DIR


def _safe_filename(original: str, content_type: str) -> str:
    """Produce a collision-resistant, safe filename."""
    ext = Path(original).suffix.lower()
    if not ext:
        ext = mimetypes.guess_extension(content_type) or ".bin"
    safe_stem = re.sub(r"[^\w\-]", "_", Path(original).stem)[:40]
    uid = uuid.uuid4().hex[:8]
    return f"{safe_stem}_{uid}{ext}"


# ── Public API ────────────────────────────────────────────────────────────────

def validate_upload(file_bytes: bytes, content_type: str) -> None:
    """
    Raise ValueError if the upload is invalid:
      - content_type not in ALLOWED_TYPES
      - file_bytes exceeds MAX_FILE_SIZE
    """
    ct = content_type.split(";")[0].strip().lower()
    if ct not in ALLOWED_TYPES:
        raise ValueError(
            f"Unsupported file type '{ct}'. Allowed: images and videos."
        )
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError(
            f"File too large: {len(file_bytes) / 1_048_576:.1f} MB. Maximum is 10 MB."
        )


def save_upload(file_bytes: bytes, original_name: str, content_type: str) -> str:
    """
    Persist the upload and return a publicly-accessible URL string.

    Parameters
    ----------
    file_bytes     : raw bytes of the uploaded file
    original_name  : original client-side filename (for extension detection)
    content_type   : MIME type reported by the client
    """
    validate_upload(file_bytes, content_type)
    filename = _safe_filename(original_name, content_type)

    client, bucket = _get_minio()
    if client is not None:
        # ── MinIO path ────────────────────────────────────────────────────
        object_key = f"reports/{filename}"
        try:
            from minio import Minio

            client.put_object(
                bucket,
                object_key,
                data=io.BytesIO(file_bytes),
                length=len(file_bytes),
                content_type=content_type,
            )
            protocol = "https" if MINIO_SECURE else "http"
            url = f"{protocol}://{MINIO_ENDPOINT}/{bucket}/{object_key}"
            logger.info("MediaStore: Saved to MinIO → %s", url)
            return url
        except Exception as exc:
            logger.error("MediaStore: MinIO put_object failed: %s", exc)
            # Fall through to local storage
            global _use_minio
            _use_minio = False

    # ── Local fallback path ───────────────────────────────────────────────
    local_dir = _ensure_local_dir()
    dest = local_dir / filename
    dest.write_bytes(file_bytes)
    url = f"/media/{filename}"
    logger.info("MediaStore: Saved locally → %s", url)
    return url


def is_image(content_type: str) -> bool:
    return content_type.split(";")[0].strip().lower() in ALLOWED_IMAGE_TYPES
