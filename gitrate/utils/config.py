"""Configuration management for GitRate."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # ===== ENVIRONMENT =====
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # ===== DATABASE =====
    database_url: str = Field(default="postgresql+asyncpg://gitrate:password@localhost:5432/gitrate_audit", env="DATABASE_URL")
    db_echo: bool = Field(default=False, env="DB_ECHO")
    db_pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, env="DB_MAX_OVERFLOW")
    
    # ===== REDIS =====
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_cache_ttl: int = Field(default=86400, env="REDIS_CACHE_TTL")  # 24 hours
    
    # ===== SECURITY =====
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # 24 hours
    cors_origins: list[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # ===== GITHUB =====
    github_token: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    github_api_base_url: str = Field(default="https://api.github.com", env="GITHUB_API_BASE_URL")
    github_webhook_secret: Optional[str] = Field(default=None, env="GITHUB_WEBHOOK_SECRET")
    gitlab_webhook_secret: Optional[str] = Field(default=None, env="GITLAB_WEBHOOK_SECRET")
    
    # ===== AI/LLM =====
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-pro", env="GEMINI_MODEL")
    
    # ===== CVE DATABASE =====
    nvd_api_key: Optional[str] = Field(default=None, env="NVD_API_KEY")
    snyk_api_key: Optional[str] = Field(default=None, env="SNYK_API_KEY")
    
    # ===== CELERY =====
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    
    # ===== API RATE LIMITING =====
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    
    # ===== AUDIT SETTINGS =====
    audit_timeout_seconds: int = Field(default=300, env="AUDIT_TIMEOUT_SECONDS")
    max_repo_size_mb: int = Field(default=500, env="MAX_REPO_SIZE_MB")
    cache_audit_results: bool = Field(default=True, env="CACHE_AUDIT_RESULTS")
    
    # ===== FEATURE FLAGS =====
    enable_plagiarism_detection: bool = Field(default=True, env="ENABLE_PLAGIARISM_DETECTION")
    enable_onboarding_estimation: bool = Field(default=True, env="ENABLE_ONBOARDING_ESTIMATION")
    enable_scalability_analysis: bool = Field(default=True, env="ENABLE_SCALABILITY_ANALYSIS")
    enable_90day_roadmap: bool = Field(default=True, env="ENABLE_90DAY_ROADMAP")
    
    # ===== SENTRY =====
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    sentry_environment: str = Field(default="development", env="SENTRY_ENVIRONMENT")
    
    # ===== AWS =====
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    aws_s3_bucket: Optional[str] = Field(default=None, env="AWS_S3_BUCKET")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()
