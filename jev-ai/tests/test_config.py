"""Tests for application configuration."""

import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def load_settings(monkeypatch, **overrides):
    defaults = {
        "CLAUDE_CODE_OAUTH_TOKEN": "test-session-token",
        "TELEGRAM_BOT_TOKEN": "123456:test-token",
        "TELEGRAM_CHAT_ID": "123456789",
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        monkeypatch.setenv(key, str(value))

    sys.modules.pop("config", None)
    from config import Settings
    return Settings


def test_settings_load_required_values(monkeypatch):
    Settings = load_settings(monkeypatch)
    settings = Settings()

    assert settings.claude_code_oauth_token == "test-session-token"
    assert settings.telegram_chat_id == "123456789"
    assert settings.min_trades_90d == 20
    assert settings.position_size_usdc == 50.0


def test_settings_reject_invalid_win_rate(monkeypatch):
    Settings = load_settings(monkeypatch, MIN_WIN_RATE="1.5")

    with pytest.raises(ValidationError, match="less_than_equal"):
        Settings()


def test_settings_reject_invalid_log_level(monkeypatch):
    Settings = load_settings(monkeypatch, LOG_LEVEL="LOUD")

    with pytest.raises(ValidationError, match="value_error"):
        Settings()


def test_settings_detects_production(monkeypatch):
    Settings = load_settings(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")

    settings = Settings()
    assert settings.is_production is True
