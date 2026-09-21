"""Test suite for Jev AI configuration."""

import os
import pytest
from pydantic import ValidationError


def load_settings_class(monkeypatch, **env_overrides):
    """Dynamically load Settings class with isolated environment."""
    base_env = {
        "ENVIRONMENT": "development",
        "LOG_LEVEL": "INFO",
        "DATABASE_URL": "postgresql://jev_user:jev_pass@localhost:5432/jev_ai",
        "MCP_POLYMARKET_URL": "http://localhost:8081",
        "MCP_TELEGRAM_URL": "http://localhost:8082",
        "POSITION_SIZE_USDC": "50.0",
        "MAX_POSITIONS": "10",
        "COPY_SELLS": "true",
        "POLL_INTERVAL_SECS": "60",
        "MIN_TRADES_90D": "20",
        "MIN_LIFETIME_PNL": "10000.0",
        "MIN_WIN_RATE": "0.20",
        "TELEGRAM_BOT_TOKEN": "123456:test-token",
        "TELEGRAM_CHAT_ID": "123456789",
    }
    base_env.update(env_overrides)
    for key, value in base_env.items():
        monkeypatch.setenv(key, value)

    from config import Settings
    return Settings


def test_settings_load_required_values(monkeypatch):
    Settings = load_settings_class(monkeypatch)
    settings = Settings()

    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.database_url == "postgresql://jev_user:jev_pass@localhost:5432/jev_ai"
    assert settings.position_size_usdc == 50.0
    assert settings.max_positions == 10
    assert settings.min_trades_90d == 20
    assert settings.min_lifetime_pnl == 10000.0
    assert settings.min_win_rate == 0.20
    assert settings.telegram_bot_token == "123456:test-token"
    assert settings.telegram_chat_id == "123456789"


def test_settings_reject_invalid_win_rate(monkeypatch):
    Settings = load_settings_class(monkeypatch, MIN_WIN_RATE="1.5")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "min_win_rate" in str(exc_info.value)


def test_settings_reject_invalid_log_level(monkeypatch):
    Settings = load_settings_class(monkeypatch, LOG_LEVEL="LOUD")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "log_level" in str(exc_info.value)


def test_settings_detects_production(monkeypatch):
    Settings = load_settings_class(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")

    settings = Settings()
    assert settings.is_production is True
    assert settings.environment == "production"


def test_settings_reject_production_without_telegram(monkeypatch):
    Settings = load_settings_class(monkeypatch, TELEGRAM_BOT_TOKEN="", ENVIRONMENT="production")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "TELEGRAM_BOT_TOKEN" in str(exc_info.value)


def test_settings_accept_valid_log_levels(monkeypatch):
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        Settings = load_settings_class(monkeypatch, LOG_LEVEL=level)
        settings = Settings()
        assert settings.log_level == level
