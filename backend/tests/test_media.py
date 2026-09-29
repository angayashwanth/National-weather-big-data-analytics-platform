"""
backend/tests/test_media.py

Unit / integration tests for:
  - POST /api/media endpoint (multipart upload)
  - media_store.py (validate_upload, save_upload local-fallback)
  - pipeline.py phash helpers (_phash_from_bytes, _phash_list, _any_phash_near_duplicate)
  - find_duplicate() with photos kwarg

No live MinIO required – all tests use the local-folder fallback.
No live network calls.
"""

from __future__ import annotations

import io
import os
import struct
import tempfile
from pathlib import Path

import pytest

# ── Tiny synthetic images ─────────────────────────────────────────────────────

def _make_png(color_rgb: tuple[int, int, int] = (255, 0, 0), size: int = 64) -> bytes:
    """Create a minimal solid-colour PNG using Pillow."""
    from PIL import Image
    img = Image.new("RGB", (size, size), color_rgb)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_pattern_png(pattern: str = "checker", shift: int = 0, size: int = 64) -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (size, size), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    if pattern == "checker":
        for x in range(0, size, 8):
            for y in range(0, size, 8):
                if (x // 8 + y // 8) % 2 == 0:
                    draw.rectangle([x, y, x + 7, y + 7], fill=(0, 0, 0))
    elif pattern == "circles":
        for r in range(4, size // 2, 6):
            draw.ellipse([size // 2 - r + shift, size // 2 - r, size // 2 + r + shift, size // 2 + r], outline=(255, 0, 0), width=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


SMALL_RED_PNG        = _make_png((255, 0, 0))
SMALL_GREEN_PNG      = _make_png((0, 255, 0))
PATTERN_CHECKER_PNG  = _make_pattern_png("checker")
PATTERN_CIRCLES_PNG  = _make_pattern_png("circles", shift=0)
PATTERN_CIRCLES_NEAR = _make_pattern_png("circles", shift=1)
TINY_TEXT            = b"not an image at all"


# ═══════════════════════════════════════════════════════════════════════════════
# media_store unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidateUpload:

    def setup_method(self):
        from backend.app.media_store import validate_upload
        self.fn = validate_upload

    def test_valid_jpeg(self):
        self.fn(b"x" * 100, "image/jpeg")  # should not raise

    def test_valid_video_mp4(self):
        self.fn(b"x" * 1000, "video/mp4")

    def test_invalid_type_pdf(self):
        with pytest.raises(ValueError, match="Unsupported"):
            self.fn(b"x" * 100, "application/pdf")

    def test_invalid_type_text(self):
        with pytest.raises(ValueError, match="Unsupported"):
            self.fn(b"x" * 100, "text/plain")

    def test_too_large(self):
        from backend.app.media_store import MAX_FILE_SIZE
        with pytest.raises(ValueError, match="too large"):
            self.fn(b"x" * (MAX_FILE_SIZE + 1), "image/jpeg")

    def test_exactly_max_size_ok(self):
        from backend.app.media_store import MAX_FILE_SIZE
        self.fn(b"x" * MAX_FILE_SIZE, "image/png")  # should not raise

    def test_content_type_with_charset_stripped(self):
        # "image/jpeg; charset=utf-8" should be treated as image/jpeg
        self.fn(b"x" * 100, "image/jpeg; charset=utf-8")

    def test_image_webp_allowed(self):
        self.fn(b"x" * 100, "image/webp")

    def test_video_webm_allowed(self):
        self.fn(b"x" * 100, "video/webm")


class TestSaveUploadLocal:
    """Test that save_upload uses the local-folder fallback when MINIO_ENDPOINT is unset."""

    def test_saves_file_and_returns_media_url(self, tmp_path, monkeypatch):
        import backend.app.media_store as ms
        monkeypatch.setattr(ms, "MINIO_ENDPOINT", "")
        monkeypatch.setattr(ms, "_use_minio", False)
        monkeypatch.setattr(ms, "MEDIA_LOCAL_DIR", tmp_path)

        url = ms.save_upload(SMALL_RED_PNG, "test.png", "image/png")
        assert url.startswith("/media/")
        filename = url.lstrip("/media/")
        assert (tmp_path / filename).exists()
        assert (tmp_path / filename).read_bytes() == SMALL_RED_PNG

    def test_safe_filename_no_path_traversal(self, tmp_path, monkeypatch):
        import backend.app.media_store as ms
        monkeypatch.setattr(ms, "MINIO_ENDPOINT", "")
        monkeypatch.setattr(ms, "_use_minio", False)
        monkeypatch.setattr(ms, "MEDIA_LOCAL_DIR", tmp_path)

        url = ms.save_upload(SMALL_RED_PNG, "../../etc/passwd.png", "image/png")
        assert ".." not in url

    def test_returns_unique_urls_for_same_content(self, tmp_path, monkeypatch):
        import backend.app.media_store as ms
        monkeypatch.setattr(ms, "MINIO_ENDPOINT", "")
        monkeypatch.setattr(ms, "_use_minio", False)
        monkeypatch.setattr(ms, "MEDIA_LOCAL_DIR", tmp_path)

        url1 = ms.save_upload(SMALL_RED_PNG, "photo.png", "image/png")
        url2 = ms.save_upload(SMALL_RED_PNG, "photo.png", "image/png")
        assert url1 != url2  # UUID suffix ensures uniqueness


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/media endpoint tests (httpx async client)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestMediaEndpoint:

    async def test_upload_png_returns_201(self, async_client, tmp_path, monkeypatch):
        import backend.app.media_store as ms
        monkeypatch.setattr(ms, "MINIO_ENDPOINT", "")
        monkeypatch.setattr(ms, "_use_minio", False)
        monkeypatch.setattr(ms, "MEDIA_LOCAL_DIR", tmp_path)

        resp = await async_client.post(
            "/api/media",
            files={"file": ("red.png", SMALL_RED_PNG, "image/png")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["url"].startswith("/media/")
        assert data["content_type"] == "image/png"
        assert data["size_bytes"] == len(SMALL_RED_PNG)

    async def test_upload_mp4_returns_201(self, async_client, tmp_path, monkeypatch):
        import backend.app.media_store as ms
        monkeypatch.setattr(ms, "MINIO_ENDPOINT", "")
        monkeypatch.setattr(ms, "_use_minio", False)
        monkeypatch.setattr(ms, "MEDIA_LOCAL_DIR", tmp_path)

        fake_video = b"\x00" * 512
        resp = await async_client.post(
            "/api/media",
            files={"file": ("clip.mp4", fake_video, "video/mp4")},
        )
        assert resp.status_code == 201
        assert resp.json()["url"].startswith("/media/")

    async def test_upload_pdf_rejected_415(self, async_client):
        resp = await async_client.post(
            "/api/media",
            files={"file": ("doc.pdf", b"content", "application/pdf")},
        )
        assert resp.status_code == 415

    async def test_upload_too_large_rejected_413(self, async_client):
        from backend.app.media_store import MAX_FILE_SIZE
        big = b"x" * (MAX_FILE_SIZE + 1)
        resp = await async_client.post(
            "/api/media",
            files={"file": ("big.png", big, "image/png")},
        )
        assert resp.status_code == 413

    async def test_upload_response_has_filename(self, async_client, tmp_path, monkeypatch):
        import backend.app.media_store as ms
        monkeypatch.setattr(ms, "MINIO_ENDPOINT", "")
        monkeypatch.setattr(ms, "_use_minio", False)
        monkeypatch.setattr(ms, "MEDIA_LOCAL_DIR", tmp_path)

        resp = await async_client.post(
            "/api/media",
            files={"file": ("myphoto.png", SMALL_RED_PNG, "image/png")},
        )
        assert resp.status_code == 201
        assert resp.json()["filename"] == "myphoto.png"


# ═══════════════════════════════════════════════════════════════════════════════
# Perceptual hash helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestPhashHelpers:

    def test_phash_from_bytes_returns_hash_for_valid_image(self):
        from backend.app.pipeline import _phash_from_bytes
        h = _phash_from_bytes(SMALL_RED_PNG)
        assert h is not None

    def test_phash_from_bytes_returns_none_for_invalid(self):
        from backend.app.pipeline import _phash_from_bytes
        assert _phash_from_bytes(TINY_TEXT) is None

    def test_identical_images_have_zero_distance(self):
        from backend.app.pipeline import _phash_from_bytes
        h1 = _phash_from_bytes(SMALL_RED_PNG)
        h2 = _phash_from_bytes(SMALL_RED_PNG)
        assert h1 is not None and h2 is not None
        assert abs(h1 - h2) == 0

    def test_near_duplicate_images_within_threshold(self):
        from backend.app.pipeline import _phash_from_bytes, _PHASH_THRESHOLD
        h1 = _phash_from_bytes(PATTERN_CIRCLES_PNG)
        h2 = _phash_from_bytes(PATTERN_CIRCLES_NEAR)
        assert h1 is not None and h2 is not None
        assert abs(h1 - h2) <= _PHASH_THRESHOLD

    def test_different_pattern_images_exceed_threshold(self):
        from backend.app.pipeline import _phash_from_bytes, _PHASH_THRESHOLD
        h1 = _phash_from_bytes(PATTERN_CHECKER_PNG)
        h2 = _phash_from_bytes(PATTERN_CIRCLES_PNG)
        assert h1 is not None and h2 is not None
        assert abs(h1 - h2) > _PHASH_THRESHOLD

    def test_any_phash_near_duplicate_true_for_same(self):
        from backend.app.pipeline import _phash_from_bytes, _any_phash_near_duplicate
        h = _phash_from_bytes(SMALL_RED_PNG)
        assert _any_phash_near_duplicate([h], [h]) is True

    def test_any_phash_near_duplicate_false_for_empty(self):
        from backend.app.pipeline import _any_phash_near_duplicate
        assert _any_phash_near_duplicate([], []) is False
        assert _any_phash_near_duplicate([1], []) is False

    def test_phash_list_skips_non_images(self, tmp_path, monkeypatch):
        from backend.app.pipeline import _phash_list
        import backend.app.pipeline as pl
        monkeypatch.setattr(pl, "Path", lambda x: tmp_path if "media_uploads" in str(x) else Path(x))
        # mp4 URL should be skipped
        result = _phash_list(["/media/video.mp4"])
        assert result == []

    def test_phash_list_skips_missing_files(self):
        from backend.app.pipeline import _phash_list
        result = _phash_list(["/media/definitely_does_not_exist.jpg"])
        assert result == []

    def test_phash_from_local_url_returns_hash_for_existing_file(self, tmp_path, monkeypatch):
        from backend.app.pipeline import _phash_from_local_url
        import backend.app.media_store as ms
        # Write a real image to tmp_path
        img_file = tmp_path / "test.png"
        img_file.write_bytes(SMALL_RED_PNG)
        monkeypatch.setattr(ms, "MEDIA_LOCAL_DIR", tmp_path)
        h = _phash_from_local_url("/media/test.png")
        assert h is not None


class TestMinioStorage:

    def test_minio_save_upload_success(self, monkeypatch):
        from unittest.mock import MagicMock
        import backend.app.media_store as ms

        mock_client = MagicMock()
        monkeypatch.setattr(ms, "_minio_client", mock_client)
        monkeypatch.setattr(ms, "_use_minio", True)
        monkeypatch.setattr(ms, "MINIO_ENDPOINT", "localhost:9000")
        monkeypatch.setattr(ms, "MINIO_BUCKET", "wx-media")
        monkeypatch.setattr(ms, "MINIO_SECURE", False)

        url = ms.save_upload(SMALL_RED_PNG, "satellite.png", "image/png")
        assert url.startswith("http://localhost:9000/wx-media/reports/")
        assert mock_client.put_object.called

    def test_minio_put_failure_falls_back_to_local(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock
        import backend.app.media_store as ms

        mock_client = MagicMock()
        mock_client.put_object.side_effect = Exception("MinIO network failure")
        monkeypatch.setattr(ms, "_minio_client", mock_client)
        monkeypatch.setattr(ms, "_use_minio", True)
        monkeypatch.setattr(ms, "MINIO_ENDPOINT", "localhost:9000")
        monkeypatch.setattr(ms, "MEDIA_LOCAL_DIR", tmp_path)

        url = ms.save_upload(SMALL_RED_PNG, "fallback.png", "image/png")
        assert url.startswith("/media/")
        assert ms._use_minio is False


# ═══════════════════════════════════════════════════════════════════════════════
# find_duplicate with photos kwarg (async)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestFindDuplicateWithPhotos:

    async def test_text_duplicate_still_detected(self, async_session):
        """Baseline: text-only Jaccard duplicate still works."""
        from backend.app.pipeline import find_duplicate
        from backend.app.models import Report
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        report = Report(
            timestamp=now,
            city="Mumbai",
            state="Maharashtra",
            event_category="rainfall",
            source_type="citizen_report",
            text="Heavy rain floods roads in Kurla area",
            verification_status="unverified",
            trust_score=50.0,
            photos="",
            videos="",
            high_impact=False,
        )
        async_session.add(report)
        await async_session.commit()
        await async_session.refresh(report)

        dup_id = await find_duplicate(
            text="Heavy rain floods roads in Kurla area",
            event_category="rainfall",
            city="Mumbai",
            timestamp=now,
            exclude_id=None,
            db=async_session,
            photos=[],
        )
        assert dup_id == report.id

    async def test_no_duplicate_returns_none(self, async_session):
        from backend.app.pipeline import find_duplicate
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        dup_id = await find_duplicate(
            text="Fog on the highway near Surat",
            event_category="fog",
            city="Surat",
            timestamp=now,
            exclude_id=None,
            db=async_session,
            photos=[],
        )
        assert dup_id is None

    async def test_phash_detects_duplicate_when_text_differs(self, async_session, tmp_path, monkeypatch):
        """When text has low similarity, duplicate photo in same city/time window detects duplicate."""
        from backend.app.pipeline import find_duplicate
        from backend.app.models import Report
        import backend.app.media_store as ms
        import datetime

        monkeypatch.setattr(ms, "MEDIA_LOCAL_DIR", tmp_path)

        # Write two near-identical images
        img1 = tmp_path / "img1.png"
        img1.write_bytes(PATTERN_CIRCLES_PNG)
        img2 = tmp_path / "img2.png"
        img2.write_bytes(PATTERN_CIRCLES_NEAR)

        now = datetime.datetime.now(datetime.timezone.utc)
        report = Report(
            timestamp=now,
            city="Mumbai",
            state="Maharashtra",
            event_category="rainfall",
            source_type="citizen_report",
            text="Heavy rain causing water accumulation at Hindmata junction",
            verification_status="verified",
            trust_score=75.0,
            photos="/media/img1.png",
            videos="",
            high_impact=False,
        )
        async_session.add(report)
        await async_session.commit()
        await async_session.refresh(report)

        # Incoming report has completely different wording ("Submerged bus stop near Dadar")
        # but near-duplicate photo img2.png
        dup_id = await find_duplicate(
            text="Submerged bus stop near Dadar flower market",
            event_category="rainfall",
            city="Mumbai",
            timestamp=now,
            exclude_id=None,
            db=async_session,
            photos=["/media/img2.png"],
        )
        assert dup_id == report.id

    async def test_different_images_different_text_not_duplicate(self, async_session, tmp_path, monkeypatch):
        """Different images and different text should not trigger duplicate."""
        from backend.app.pipeline import find_duplicate
        from backend.app.models import Report
        import backend.app.media_store as ms
        import datetime

        monkeypatch.setattr(ms, "MEDIA_LOCAL_DIR", tmp_path)

        img_checker = tmp_path / "checker.png"
        img_checker.write_bytes(PATTERN_CHECKER_PNG)
        img_circles = tmp_path / "circles.png"
        img_circles.write_bytes(PATTERN_CIRCLES_PNG)

        now = datetime.datetime.now(datetime.timezone.utc)
        report = Report(
            timestamp=now,
            city="Mumbai",
            state="Maharashtra",
            event_category="rainfall",
            source_type="citizen_report",
            text="Rainfall report in Colaba",
            verification_status="verified",
            trust_score=75.0,
            photos="/media/checker.png",
            videos="",
            high_impact=False,
        )
        async_session.add(report)
        await async_session.commit()
        await async_session.refresh(report)

        dup_id = await find_duplicate(
            text="Completely different rainfall observation in Borivali",
            event_category="rainfall",
            city="Mumbai",
            timestamp=now,
            exclude_id=None,
            db=async_session,
            photos=["/media/circles.png"],
        )
        assert dup_id is None
