"""
backend/app/routers/media.py – POST /api/media (multipart upload)

Accepts one file at a time, max 10 MB, image/video types only.
Stores via media_store.save_upload() (MinIO or local fallback).
Returns the URL for use in ReportCreate.photos / .videos lists.
"""


import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..media_store import save_upload, validate_upload, MAX_FILE_SIZE
from ..rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["media"])


class MediaUploadOut(BaseModel):
    url: str
    filename: str
    content_type: str
    size_bytes: int


@router.post(
    "/media",
    response_model=MediaUploadOut,
    status_code=201,
    summary="Upload a photo or video (max 10 MB). Returns a URL for use in reports.",
)
@limiter.limit("20/minute")
async def upload_media(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Multipart file upload endpoint.

    - Accepts images (JPEG, PNG, GIF, WebP, BMP, TIFF) and videos
      (MP4, MPEG, WebM, MOV, AVI, 3GPP).
    - Maximum file size: 10 MB.
    - Files are stored in MinIO (if available) or the local `media_uploads/` folder.
    - Returns a JSON object with `url` which can be added to a report's
      `photos` or `videos` list.
    """
    content_type = file.content_type or "application/octet-stream"
    original_name = file.filename or "upload.bin"

    # Read with size guard
    data = await file.read(MAX_FILE_SIZE + 1)
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is 10 MB.",
        )

    try:
        validate_upload(data, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))

    try:
        url = save_upload(data, original_name, content_type)
    except Exception as exc:
        logger.error("Media upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Storage error. Please retry.")

    return MediaUploadOut(
        url=url,
        filename=original_name,
        content_type=content_type,
        size_bytes=len(data),
    )
