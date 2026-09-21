"""Configuration settings for Jev AI."""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Environment
    environment: str = Field(default="development", description="Environment: development, test, production")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database
    database_url: str = Field(default="postgresql://jev_user:jev_pass@localhost:5432/jev_ai", description="PostgreSQL connection URL")

    # MCP Servers
    mcp_polymarket_url: str = Field(default="http://localhost:8081", description="Polymarket MCP server URL")
    mcp_telegram_url: str = Field(default="http://localhost:8082", description="Telegram MCP server URL")

    # Trading Parameters
    position_size_usdc: float = Field(default=50.0, ge=1.0, description="Position size in USDC")
    max_positions: int = Field(default=10, ge=1, description="Maximum concurrent positions")
    copy_sells: bool = Field(default=True, description="Whether to copy sell orders")
    poll_interval_secs: int = Field(default=60, ge=5, description="Wallet scan interval in seconds")

    # Wallet Selection Criteria
    min_trades_90d: int = Field(default=20, ge=1, description="Minimum trades in last 90 days")
    min_lifetime_pnl: float = Field(default=10000.0, ge=0, description="Minimum lifetime PnL in USD")
    min_win_rate: float = Field(default=0.20, ge=0.0, le=1.0, description="Minimum win rate")

    # Telegram Bot
    telegram_bot_token: str = Field(default="", description="Telegram bot token")
    telegram_chat_id: str = Field(default="", description="Telegram chat ID")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "test", "production"}
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @field_validator("telegram_bot_token", "telegram_chat_id")
    @classmethod
    def validate_telegram_required_in_prod(cls, v: str, info) -> str:
        if info.data.get("environment") == "production" and not v:
            raise ValueError("Telegram credentials are required in production")
        return v


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
