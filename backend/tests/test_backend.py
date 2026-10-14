"""
Backend tests — auth, API keys, analysis pipeline, validators.
Run with: pytest tests/ -v
"""
import io
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

# ─────────────────────────────────────────────────────────────
# Security utils tests
# ─────────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_and_verify(self):
        from app.utils.security import hash_password, verify_password
        pwd = "SecureP@ss123"
        h = hash_password(pwd)
        assert h != pwd
        assert verify_password(pwd, h)

    def test_wrong_password_fails(self):
        from app.utils.security import hash_password, verify_password
        h = hash_password("correct")
        assert not verify_password("wrong", h)


class TestAPIKeyGeneration:
    def test_format_live(self):
        from app.utils.security import generate_api_key
        full, prefix, key_hash = generate_api_key("production")
        assert full.startswith("dg_live_")
        assert len(full) > 40
        assert key_hash != full

    def test_format_test(self):
        from app.utils.security import generate_api_key
        full, prefix, key_hash = generate_api_key("development")
        assert full.startswith("dg_test_")

    def test_hash_uniqueness(self):
        from app.utils.security import generate_api_key, hash_api_key
        k1, _, _ = generate_api_key()
        k2, _, _ = generate_api_key()
        assert k1 != k2
        assert hash_api_key(k1) != hash_api_key(k2)

    def test_verify_api_key(self):
        from app.utils.security import generate_api_key, verify_api_key
        full, _, stored_hash = generate_api_key()
        assert verify_api_key(full, stored_hash)
        assert not verify_api_key("dg_live_wrong", stored_hash)


class TestOTP:
    def test_generate_6_digits(self):
        from app.utils.security import generate_otp
        for _ in range(20):
            otp = generate_otp()
            assert len(otp) == 6
            assert otp.isdigit()

    def test_hash_and_verify(self):
        from app.utils.security import generate_otp, hash_otp, verify_otp
        otp = generate_otp()
        h = hash_otp(otp)
        assert verify_otp(otp, h)
        assert not verify_otp("000000", h)


class TestJWT:
    def test_create_and_decode(self):
        from app.utils.security import create_access_token, decode_access_token
        token = create_access_token(subject="user123")
        payload = decode_access_token(token)
        assert payload["sub"] == "user123"

    def test_invalid_token_raises(self):
        from fastapi import HTTPException
        from app.utils.security import decode_access_token
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("invalid.token.here")
        assert exc_info.value.status_code == 401


# ─────────────────────────────────────────────────────────────
# Image validator tests
# ─────────────────────────────────────────────────────────────

class TestImageValidator:
    def _make_upload(self, content_type="image/jpeg", filename="test.jpg", data=b""):
        from fastapi import UploadFile
        upload = MagicMock(spec=UploadFile)
        upload.content_type = content_type
        upload.filename = filename
        upload.read = AsyncMock(return_value=data)
        return upload

    @pytest.mark.asyncio
    async def test_rejects_exe(self):
        from fastapi import HTTPException
        from app.utils.validators import validate_image_upload
        upload = self._make_upload("application/octet-stream", "malware.exe", b"MZ")
        with pytest.raises(HTTPException) as exc:
            await validate_image_upload(upload, 10 * 1024 * 1024)
        assert exc.value.status_code in (413, 422)

    @pytest.mark.asyncio
    async def test_rejects_oversized(self):
        from fastapi import HTTPException
        from app.utils.validators import validate_image_upload
        # Create a fake JPEG with correct content type but oversized
        upload = self._make_upload("image/jpeg", "big.jpg", b"x" * (20 * 1024 * 1024))
        with pytest.raises(HTTPException) as exc:
            await validate_image_upload(upload, 10 * 1024 * 1024)
        assert exc.value.status_code == 413

    @pytest.mark.asyncio
    async def test_rejects_empty(self):
        from fastapi import HTTPException
        from app.utils.validators import validate_image_upload
        upload = self._make_upload("image/jpeg", "empty.jpg", b"")
        with pytest.raises(HTTPException) as exc:
            await validate_image_upload(upload, 10 * 1024 * 1024)
        assert exc.value.status_code in (413, 422)


# ─────────────────────────────────────────────────────────────
# Provenance detector tests
# ─────────────────────────────────────────────────────────────

class TestSignatureDetector:
    def _minimal_png(self) -> bytes:
        """Return a minimal valid PNG bytes (8x8 white)."""
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new("RGB", (8, 8), color=(255, 255, 255))
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _png_with_text(self, key: str, value: str) -> bytes:
        from PIL import Image, PngImagePlugin
        buf = io.BytesIO()
        img = Image.new("RGB", (8, 8), color=(255, 255, 255))
        meta = PngImagePlugin.PngInfo()
        meta.add_text(key, value)
        img.save(buf, format="PNG", pnginfo=meta)
        return buf.getvalue()

    def test_no_indicator_on_clean_image(self):
        from app.services.signature_detector import detect_provenance
        result = detect_provenance(self._minimal_png())
        assert result["status"] == "no_indicator_found"

    def test_detects_stable_diffusion_metadata(self):
        from app.services.signature_detector import detect_provenance
        raw = self._png_with_text("Software", "stable diffusion")
        result = detect_provenance(raw)
        assert result["status"] == "indicator_found"
        assert "Stable Diffusion" in result["provider"]

    def test_detects_midjourney(self):
        from app.services.signature_detector import detect_provenance
        raw = self._png_with_text("Comment", "Created by midjourney v5")
        result = detect_provenance(raw)
        assert result["status"] == "indicator_found"


# ─────────────────────────────────────────────────────────────
# Metadata analyzer tests
# ─────────────────────────────────────────────────────────────

class TestMetadataAnalyzer:
    def _minimal_png(self) -> bytes:
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new("RGB", (8, 8), color=(128, 128, 128))
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_minimal_image_no_exif(self):
        from app.services.metadata_analyzer import analyze_metadata
        result = analyze_metadata(self._minimal_png())
        assert result["has_exif"] == False
        assert result["metadata_integrity"] == "missing"

    def test_invalid_bytes(self):
        from app.services.metadata_analyzer import analyze_metadata
        result = analyze_metadata(b"not an image")
        assert "error" in result["explanation"].lower() or result["has_exif"] == False


# ─────────────────────────────────────────────────────────────
# Ensemble tests (no real TF models needed — mock)
# ─────────────────────────────────────────────────────────────

class TestEnsemble:
    def _make_registry(self, scores: dict):
        from app.ml.model_loader import ModelRegistry, LoadedModel
        models = {}
        for k, score in scores.items():
            mock_model = MagicMock()
            import numpy as np
            mock_model.predict = MagicMock(return_value=np.array([[score]]))
            models[k] = LoadedModel(
                key=k,
                display_name=k,
                description="",
                model=mock_model,
                input_shape=(None, 224, 224, 3),
                status="loaded",
            )
        return ModelRegistry(models=models)

    def _minimal_image(self) -> bytes:
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new("RGB", (224, 224), color=(100, 100, 100))
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_likely_real(self):
        from app.ml.ensemble import run_ensemble
        registry = self._make_registry({"m1": 0.9, "m2": 0.85, "m3": 0.88})
        result = run_ensemble(self._minimal_image(), registry)
        assert result.ensemble_label == "likely_real"
        assert result.models_run == 3

    def test_likely_fake(self):
        from app.ml.ensemble import run_ensemble
        registry = self._make_registry({"m1": 0.1, "m2": 0.15, "m3": 0.2})
        result = run_ensemble(self._minimal_image(), registry)
        assert result.ensemble_label == "likely_fake"

    def test_empty_registry(self):
        from app.ml.model_loader import ModelRegistry
        from app.ml.ensemble import run_ensemble
        result = run_ensemble(self._minimal_image(), ModelRegistry(models={}))
        assert result.ensemble_label == "inconclusive"
        assert result.models_run == 0


# ─────────────────────────────────────────────────────────────
# Evidence fusion tests
# ─────────────────────────────────────────────────────────────

class TestEvidenceFusion:
    def _make_provenance(self, status, confidence=0.9):
        from app.models.analysis import ProvenanceResult
        return ProvenanceResult(
            status=status,
            provider="TestAI" if status == "indicator_found" else None,
            confidence=confidence,
            explanation="",
        )

    def _make_metadata(self, integrity="missing"):
        from app.models.analysis import MetadataResult
        return MetadataResult(metadata_integrity=integrity, explanation="")

    def _make_ensemble(self, label, score):
        from app.models.analysis import EnsembleResult
        return EnsembleResult(ensemble_label=label, ensemble_score=score, models_run=3)

    def test_strong_fake_evidence(self):
        from app.services.analysis_service import _fuse_evidence
        prov = self._make_provenance("indicator_found", 0.9)
        meta = self._make_metadata("missing")
        ens = self._make_ensemble("likely_fake", 0.1)
        assessment, confidence, _, _ = _fuse_evidence(prov, meta, ens)
        assert assessment in ("likely_ai_generated", "likely_manipulated", "suspicious")
        assert confidence > 0.5

    def test_strong_real_evidence(self):
        from app.services.analysis_service import _fuse_evidence
        prov = self._make_provenance("no_indicator_found", 0.05)
        meta = self._make_metadata("consistent")
        ens = self._make_ensemble("likely_real", 0.92)
        assessment, confidence, _, _ = _fuse_evidence(prov, meta, ens)
        assert assessment == "likely_authentic"
        assert confidence > 0.5
