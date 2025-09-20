"""Application configuration settings."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "TrueTrend Diabetes Analytics"
    app_version: str = "1.0.0-MVP"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/trutrend_dev"
    
    # Security
    secret_key: str = "trutrend-development-key-change-in-production"
    encryption_key: str = "development-encryption-key-32-bytes"
    
    # File Upload
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    upload_dir: str = "/tmp/trutrend_uploads"
    
    # Clinical Rules Thresholds
    postprandial_threshold: float = 180.0  # mg/dL
    postprandial_window: int = 120  # minutes
    mistimed_bolus_threshold: float = 160.0  # mg/dL
    mistimed_bolus_delay: int = 10  # minutes
    
    # HIPAA/GDPR Compliance
    data_retention_days: int = 2555  # 7 years
    audit_logging: bool = True
    encryption_at_rest: bool = True
    
    # Glooko API (stub)
    glooko_api_url: str = "https://api.glooko.com/v1"
    glooko_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"


settings = Settings()