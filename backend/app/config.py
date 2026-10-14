"""
DeepGuard Configuration
Reads all settings from environment variables / .env file.
Never hard-code secrets here.
"""
import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


# Resolve the path to the existing trained models directory
_BACKEND_DIR = Path(__file__).resolve().parent.parent          # backend/
_PROJECT_ROOT = _BACKEND_DIR.parent                            # deepguard/
_MODELS_DEFAULT = _PROJECT_ROOT.parent / "model_train"         # ../model_train (original)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",),  # allow model_* field names
    )

    # -- Application ----------------------------------------------------------
    app_name: str = "DeepGuard"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # -- MySQL ----------------------------------------------------------------
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "deepguard"

    # -- JWT ------------------------------------------------------------------
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION_USE_LONG_RANDOM_STRING"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24  # 24 hours

    # -- OTP ------------------------------------------------------------------
    otp_expiration_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_dev_mode: bool = True          # If True, print OTP to console (no email)

    # -- Email / SMTP ---------------------------------------------------------
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@deepguard.ai"
    smtp_use_tls: bool = True

    # -- Storage --------------------------------------------------------------
    storage_type: str = "local"                    # "local" | "s3"
    storage_path: str = str(_BACKEND_DIR / "storage" / "uploads")
    max_upload_size_mb: int = 10

    # -- S3 (optional) --------------------------------------------------------
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_endpoint_url: str = ""        # For MinIO / compatible services

    # -- Rate Limiting --------------------------------------------------------
    rate_limit_per_minute: int = 30
    rate_limit_per_day: int = 500

    # -- ML Models ------------------------------------------------------------
    model_directory: str = str(_MODELS_DEFAULT)
    model_input_size: int = 224        # square input dimension
    model_version: str = "v1"

    # -- CORS -----------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # -- Redis (optional -- for production rate limiting) ---------------------
    redis_url: str = ""

    # -- Admin ----------------------------------------------------------------
    admin_email: str = ""

    # -- Cleanup jobs ---------------------------------------------------------
    cleanup_interval_hours: int = 6

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        return v  # kept as comma-separated string; split at use site

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def mysql_url(self) -> str:
        """Async SQLAlchemy connection URL for MySQL."""
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    @property
    def model_dir(self) -> Path:
        p = Path(self.model_directory)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def upload_dir(self) -> Path:
        p = Path(self.storage_path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
