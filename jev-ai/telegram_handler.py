"""
Telegram Handler Module

Provides Telegram bot interface for copy trading control.
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import structlog
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from config import settings
from database import Database

logger = structlog.get_logger()


class TelegramHandler:
    """Telegram bot handler for copy trading control."""
    
    def __init__(
        self,
        db: Database,
        bot_token: str,
        chat_id: str,
        mcp_telegram_url: str,
    ):
        self.db = db
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.mcp_url = mcp_telegram_url
        self._bot: Optional[Bot] = None
        self._dp: Optional[Dispatcher] = None
    
    async def initialize(self) -> None:
        """Initialize bot and dispatcher"""
        self._bot = Bot(token=self.bot_token)
        self._dp = Dispatcher()
        
        self._dp.message.register(self.cmd_start, CommandStart())
        self._dp.message.register(self.cmd_whales, Command("whales"))
        self._dp.message.register(self.cmd_follow, Command("follow"))
        self._dp.message.register(self.cmd_unfollow, Command("unfollow"))
        self._dp.message.register(self.cmd_positions, Command("positions"))
        self._dp.message.register(self.cmd_pnl, Command("pnl"))
        self._dp.message.register(self.cmd_alerts, Command("alerts"))
        self._dp.message.register(self.cmd_config, Command("config"))
        self._dp.message.register(self.cmd_help, Command("help"))
        
        logger.info("Telegram handler initialized")
    
    async def close(self) -> None:
        """Close bot"""
        if self._bot:
            await self._bot.close()
    
    async def start_polling(self) -> None:
        """Start polling for messages"""
        if self._dp and self._bot:
            await self._dp.start_polling(self._bot)
    
    async def cmd_start(self, message: Message) -> None:
        """Handle /start command"""
        text = "👋 Welcome to Jev AI Copy Trading"
        await message.answer(text)
    
    async def cmd_whales(self, message: Message) -> None:
        """Handle /whales command"""
        wallets = await self.db.fetch_all(
            "SELECT wallet_address, lifetime_pnl_usd, trades_90d, win_rate FROM followed_wallets ORDER BY lifetime_pnl_usd DESC LIMIT 10"
        )
        
        if not wallets:
            await message.answer("No wallets tracked yet.")
            return
        
        text = "🐋 Top Profitable Wallets\n\n"
        for i, w in enumerate(wallets, 1):
            text += f"{i}. {w['wallet_address'][:10]}... PnL: ${w['lifetime_pnl_usd']:,.0f}\n"
        
        await message.answer(text)
    
    async def cmd_follow(self, message: Message) -> None:
        """Handle /follow command"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Usage: /follow <wallet_address>")
            return
        
        wallet_address = args[1]
        
        if not wallet_address.startswith("0x") or len(wallet_address) != 42:
            await message.answer("Invalid wallet address format.")
            return
        
        await self.db.execute(
            "INSERT INTO followed_wallets (wallet_address, is_active) VALUES (:address, true) ON CONFLICT (wallet_address) DO UPDATE SET is_active = true",
            {"address": wallet_address}
        )
        
        await message.answer(f"✅ Now following {wallet_address[:10]}...")
    
    async def cmd_unfollow(self, message: Message) -> None:
        """Handle /unfollow command"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Usage: /unfollow <wallet_address>")
            return
        
        wallet_address = args[1]
        
        await self.db.execute(
            "UPDATE followed_wallets SET is_active = false WHERE wallet_address = :address",
            {"address": wallet_address}
        )
        
        await message.answer(f"❌ Stopped following {wallet_address[:10]}...")
    
    async def cmd_positions(self, message: Message) -> None:
        """Handle /positions command"""
        positions = await self.db.fetch_all(
            "SELECT market_question, outcome, side, shares_purchased, avg_price, total_cost_usd, unrealized_pnl_usd FROM copy_trades WHERE status = 'open' ORDER BY created_at DESC LIMIT 10"
        )
        
        if not positions:
            await message.answer("No open positions.")
            return
        
        text = "📊 Open Copy Trades\n\n"
        for pos in positions:
            pnl_icon = "🟢" if pos["unrealized_pnl_usd"] >= 0 else "🔴"
            text += f"{pnl_icon} {pos['outcome']} ({pos['side']})\n"
            text += f"   {pos['market_question'][:50]}...\n"
            text += f"   PnL: ${pos['unrealized_pnl_usd']:,.2f}\n\n"
        
        await message.answer(text)
    
    async def cmd_pnl(self, message: Message) -> None:
        """Handle /pnl command"""
        realized = await self.db.fetch_one(
            "SELECT COALESCE(SUM(realized_pnl_usd), 0) as total FROM copy_trades WHERE status = 'closed'"
        )
        
        unrealized = await self.db.fetch_one(
            "SELECT COALESCE(SUM(unrealized_pnl_usd), 0) as total FROM copy_trades WHERE status = 'open'"
        )
        
        total_realized = realized["total"] if realized else 0
        total_unrealized = unrealized["total"] if unrealized else 0
        
        text = f"💰 PnL Breakdown\n\n"
        text += f"Realized: ${total_realized:,.2f}\n"
        text += f"Unrealized: ${total_unrealized:,.2f}\n"
        text += f"Total: ${total_realized + total_unrealized:,.2f}\n"
        
        await message.answer(text)
    
    async def cmd_alerts(self, message: Message) -> None:
        """Handle /alerts command"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Usage: /alerts on|off")
            return
        
        state = args[1].lower()
        enabled = state == "on"
        
        await self.db.execute(
            "UPDATE alert_config SET alerts_enabled = :enabled WHERE chat_id = :chat_id",
            {"enabled": enabled, "chat_id": self.chat_id}
        )
        
        status = "✅ enabled" if enabled else "❌ disabled"
        await message.answer(f"Trade alerts {status}")
    
    async def cmd_config(self, message: Message) -> None:
        """Handle /config command"""
        text = f"⚙️ Configuration\n\n"
        text += f"Min trades (90d): {settings.min_trades_90d}\n"
        text += f"Min PnL: ${settings.min_lifetime_pnl:,.0f}\n"
        text += f"Min win rate: {settings.min_win_rate*100:.0f}%\n"
        text += f"Max positions: {settings.max_positions}\n"
        text += f"Position size: ${settings.position_size_usdc:.0f}\n"
        
        await message.answer(text)
    
    async def cmd_help(self, message: Message) -> None:
        """Handle /help command"""
        text = "📚 Jev AI Help\n\n"
        text += "/start - Initialize\n"
        text += "/whales - Top wallets\n"
        text += "/follow <addr> - Follow wallet\n"
        text += "/unfollow <addr> - Unfollow\n"
        text += "/positions - Open trades\n"
        text += "/pnl - PnL breakdown\n"
        text += "/alerts on|off - Toggle alerts\n"
        text += "/config - Configuration\n"
        text += "/help - This message\n"
        
        await message.answer(text)
    
    async def send_alert(self, message: str, parse_mode: str = "Markdown") -> None:
        """Send an alert message"""
        if self._bot:
            try:
                await self._bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=parse_mode,
                )
            except Exception as e:
                logger.error("Failed to send alert", error=str(e))
    
    async def _get_following_count(self) -> int:
        """Get count of followed wallets"""
        result = await self.db.fetch_one(
            "SELECT COUNT(*) FROM followed_wallets WHERE is_active = true"
        )
        return result["count"] if result else 0
    
    async def _get_open_positions_count(self) -> int:
        """Get count of open positions"""
        result = await self.db.fetch_one(
            "SELECT COUNT(*) FROM copy_trades WHERE status = 'open'"
        )
        return result["count"] if result else 0
    
    async def _get_total_pnl(self) -> float:
        """Get total PnL"""
        result = await self.db.fetch_one(
            "SELECT COALESCE(SUM(realized_pnl_usd), 0) + COALESCE(SUM(unrealized_pnl_usd), 0) as total FROM copy_trades"
        )
        return result["total"] if result else 0
