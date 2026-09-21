"""Telegram Handler Module."""

from typing import Optional
import structlog
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from config import get_settings
from database import Database

logger = structlog.get_logger()


class TelegramHandler:
    """Telegram command handler for the copy-trading control plane."""

    def __init__(self, db: Database, bot_token: str, chat_id: str, mcp_telegram_url: str):
        self.db = db
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.mcp_url = mcp_telegram_url
        self._bot: Optional[Bot] = None
        self._dp: Optional[Dispatcher] = None

    async def initialize(self) -> None:
        self._bot = Bot(token=self.bot_token)
        self._dp = Dispatcher()
        self._dp.message.register(self.cmd_start, CommandStart())
        self._dp.message.register(self.cmd_help, Command("help"))
        self._dp.message.register(self.cmd_whales, Command("whales"))
        self._dp.message.register(self.cmd_positions, Command("positions"))
        self._dp.message.register(self.cmd_pnl, Command("pnl"))

    async def close(self) -> None:
        if self._bot:
            await self._bot.close()

    async def start_polling(self) -> None:
        if self._bot and self._dp:
            await self._dp.start_polling(self._bot)

    async def cmd_start(self, message: Message) -> None:
        await message.answer("Jev AI is online. Use /help for commands.")

    async def cmd_help(self, message: Message) -> None:
        await message.answer("/whales - wallets\n/positions - positions\n/pnl - performance")

    async def cmd_whales(self, message: Message) -> None:
        wallets = await self.db.fetch_all("SELECT wallet_address, lifetime_pnl_usd FROM followed_wallets WHERE is_active = true ORDER BY lifetime_pnl_usd DESC LIMIT 10")
        if not wallets:
            await message.answer("No wallets tracked yet.")
            return
        text = "\n".join(f"{i}. {w['wallet_address'][:10]}… ${w['lifetime_pnl_usd']:,.0f}" for i, w in enumerate(wallets, 1))
        await message.answer(text)

    async def cmd_positions(self, message: Message) -> None:
        result = await self.db.fetch_one("SELECT COUNT(*) AS count FROM copy_trades WHERE status = 'open'")
        await message.answer(f"Open positions: {result['count'] if result else 0}")

    async def cmd_pnl(self, message: Message) -> None:
        result = await self.db.fetch_one("SELECT COALESCE(SUM(realized_pnl_usd), 0) AS total FROM copy_trades")
        await message.answer(f"Realized PnL: ${result['total'] if result else 0:,.2f}")

    async def send_alert(self, message: str, parse_mode: str = "Markdown") -> None:
        if self._bot:
            await self._bot.send_message(chat_id=self.chat_id, text=message, parse_mode=parse_mode)
