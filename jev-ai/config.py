"""
Jev AI Configuration Module
Loads environment variables and validates settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # CLAUDE CODE SESSION
    claude_code_oauth_token: str = Field(
        default="test-session-token",
        description="Claude Code OAuth session token"
    )
    
    # TELEGRAM
    telegram_bot_token: str = Field(
        default="123456:test-token",
        description="Telegram bot token"
    )
    
    telegram_chat_id: str = Field(
        default="123456789",
        description="Telegram chat ID"
    )
    
    # MCP SERVERS
    mcp_telegram_url: str = Field(
        default="http://localhost:8765",
        description="Telegram MCP server URL"
    )
    
    mcp_polymarket_url: str = Field(
        default="http://localhost:8766",
        description="Polymarket MCP server URL"
    )
    
    # DATABASE
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/polymarket",
        description="PostgreSQL connection string"
    )
    
    # COPY TRADING RULES
    min_trades_90d: int = Field(default=20, ge=1)
    min_lifetime_pnl: float = Field(default=10000.0, ge=0)
    min_win_rate: float = Field(default=0.20, ge=0.0, le=1.0)
    max_positions: int = Field(default=10, ge=1, le=50)
    position_size_usdc: float = Field(default=50.0, ge=1.0)
    copy_sells: bool = Field(default=True)
    poll_interval_secs: int = Field(default=60, ge=10)
    
    # POLYMARKET API
    gamma_api_url: str = Field(default="https://gamma-api.polymarket.com")
    gamma_requires_auth: bool = Field(default=False)
    
    # LOGGING
    log_level: str = Field(default="INFO")
    log_file: Optional[str] = Field(default=None)
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @property
    def is_production(self) -> bool:
        return os.getenv('ENVIRONMENT', 'development') == 'production'
    
    @property
    def debug_mode(self) -> bool:
        return self.log_level == 'DEBUG'


settings = Settings()


def get_settings() -> Settings:
    return settings
