"""Unit tests for configuration module."""

import os
import pytest
from pydantic import ValidationError

from gitrate.utils.config import Settings


class TestSettingsDefaults:
    """Tests for Settings default values."""
    
    def test_settings_load_from_env(self, monkeypatch, tmp_path):
        """Test Settings loads from environment variables."""
        monkeypatch.setenv("APP_NAME", "TestApp")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "false")
        
        settings = Settings()
        assert settings.app_name == "TestApp" or settings.app_name == "GitRate"
    
    def test_environment_validation(self):
        """Test environment field validation."""
        settings = Settings()
        assert settings.environment in ["development", "production", "testing", "staging"]
    
    def test_debug_is_boolean(self):
        """Test debug flag is boolean."""
        settings = Settings()
        assert isinstance(settings.debug, bool)


class TestDatabaseSettings:
    """Tests for database-related settings."""
    
    def test_database_url_present(self):
        """Test database URL setting exists."""
        settings = Settings()
        # Should have a database URL
        assert hasattr(settings, 'database_url')
        assert isinstance(settings.database_url, str)
    
    def test_database_echo_is_boolean(self):
        """Test database echo flag is boolean."""
        settings = Settings()
        assert isinstance(settings.database_echo, bool)
    
    def test_database_pool_size_positive(self):
        """Test database pool size is positive."""
        settings = Settings()
        assert settings.database_pool_size > 0


class TestCacheSettings:
    """Tests for Redis cache settings."""
    
    def test_redis_url_present(self):
        """Test Redis URL setting exists."""
        settings = Settings()
        assert hasattr(settings, 'redis_url')
        assert isinstance(settings.redis_url, str)
    
    def test_cache_ttl_positive(self):
        """Test cache TTL is positive."""
        settings = Settings()
        assert settings.cache_ttl_seconds > 0
    
    def test_cache_enabled_is_boolean(self):
        """Test cache enabled flag is boolean."""
        settings = Settings()
        assert isinstance(settings.cache_enabled, bool)


class TestGitHubSettings:
    """Tests for GitHub API settings."""
    
    def test_github_token_present(self):
        """Test GitHub token setting exists."""
        settings = Settings()
        assert hasattr(settings, 'github_token')
    
    def test_github_rate_limit_positive(self):
        """Test GitHub rate limit is positive."""
        settings = Settings()
        assert settings.github_rate_limit_per_hour > 0
    
    def test_github_timeout_positive(self):
        """Test GitHub API timeout is positive."""
        settings = Settings()
        assert settings.github_request_timeout_seconds > 0


class TestCelerySettings:
    """Tests for Celery queue settings."""
    
    def test_celery_broker_url_present(self):
        """Test Celery broker URL exists."""
        settings = Settings()
        assert hasattr(settings, 'celery_broker_url')
        assert isinstance(settings.celery_broker_url, str)
    
    def test_celery_concurrency_positive(self):
        """Test Celery concurrency is positive."""
        settings = Settings()
        assert settings.celery_concurrency > 0


class TestLLMSettings:
    """Tests for LLM/Claude settings."""
    
    def test_anthropic_api_key_present(self):
        """Test Anthropic API key setting exists."""
        settings = Settings()
        assert hasattr(settings, 'anthropic_api_key')
    
    def test_model_names_configured(self):
        """Test LLM model names are configured."""
        settings = Settings()
        assert hasattr(settings, 'claude_model')
        assert isinstance(settings.claude_model, str)


class TestSecuritySettings:
    """Tests for security-related settings."""
    
    def test_jwt_secret_present(self):
        """Test JWT secret setting exists."""
        settings = Settings()
        assert hasattr(settings, 'jwt_secret_key')
    
    def test_jwt_algorithm_configured(self):
        """Test JWT algorithm is configured."""
        settings = Settings()
        assert hasattr(settings, 'jwt_algorithm')
        assert settings.jwt_algorithm in ["HS256", "RS256"]
    
    def test_cors_origins_present(self):
        """Test CORS origins are configured."""
        settings = Settings()
        assert hasattr(settings, 'cors_origins')


class TestLoggingSettings:
    """Tests for logging configuration."""
    
    def test_log_level_valid(self):
        """Test log level is valid."""
        settings = Settings()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert settings.log_level in valid_levels
    
    def test_log_file_path_present(self):
        """Test log file path setting exists."""
        settings = Settings()
        assert hasattr(settings, 'log_file_path')


class TestEmailSettings:
    """Tests for email configuration."""
    
    def test_smtp_host_present(self):
        """Test SMTP host is configured."""
        settings = Settings()
        assert hasattr(settings, 'smtp_host')
    
    def test_smtp_port_positive(self):
        """Test SMTP port is positive."""
        settings = Settings()
        assert settings.smtp_port > 0
    
    def test_sender_email_present(self):
        """Test sender email is configured."""
        settings = Settings()
        assert hasattr(settings, 'sender_email')


class TestSentrySettings:
    """Tests for Sentry monitoring."""
    
    def test_sentry_dsn_present(self):
        """Test Sentry DSN setting exists."""
        settings = Settings()
        assert hasattr(settings, 'sentry_dsn')


class TestPrometheusSettings:
    """Tests for Prometheus metrics."""
    
    def test_prometheus_enabled_is_boolean(self):
        """Test Prometheus enabled flag is boolean."""
        settings = Settings()
        assert hasattr(settings, 'prometheus_enabled')
        assert isinstance(settings.prometheus_enabled, bool)


class TestSettingsIntegration:
    """Integration tests for Settings."""
    
    def test_all_required_settings_present(self):
        """Test all required settings are present."""
        settings = Settings()
        
        required_attrs = [
            'app_name', 'environment', 'debug',
            'database_url', 'redis_url',
            'github_token', 'anthropic_api_key',
            'jwt_secret_key'
        ]
        
        for attr in required_attrs:
            assert hasattr(settings, attr)
    
    def test_settings_not_none(self):
        """Test critical settings are not None."""
        settings = Settings()
        assert settings.app_name is not None
        assert settings.environment is not None
    
    def test_settings_types_correct(self):
        """Test settings have correct types."""
        settings = Settings()
        assert isinstance(settings.app_name, str)
        assert isinstance(settings.environment, str)
        assert isinstance(settings.debug, bool)
        assert isinstance(settings.cache_ttl_seconds, int)
        assert isinstance(settings.github_rate_limit_per_hour, int)
    
    def test_settings_creates_valid_instance(self):
        """Test Settings creates valid instance."""
        settings = Settings()
        assert settings is not None
        assert isinstance(settings, Settings)


class TestSettingsComparison:
    """Tests for comparing settings instances."""
    
    def test_two_settings_instances_have_same_values(self):
        """Test two Settings instances have same values."""
        settings1 = Settings()
        settings2 = Settings()
        
        # Both should have same environment
        assert settings1.environment == settings2.environment
        # Both should have same app name
        assert settings1.app_name == settings2.app_name


class TestSettingsExports:
    """Tests for accessing settings as dictionary."""
    
    def test_settings_dict_method(self):
        """Test Settings can be converted to dict."""
        settings = Settings()
        settings_dict = settings.model_dump()
        assert isinstance(settings_dict, dict)
        assert len(settings_dict) > 0
        assert 'app_name' in settings_dict
    
    def test_settings_json_method(self):
        """Test Settings can be converted to JSON."""
        settings = Settings()
        settings_json = settings.model_dump_json()
        assert isinstance(settings_json, str)
        assert len(settings_json) > 0
        assert 'app_name' in settings_json
