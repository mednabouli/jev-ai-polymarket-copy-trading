"""
Telegram MCP Server

Provides Model Context Protocol tools for Telegram messaging:
- send_message: Send a message to a Telegram chat
- get_updates: Get recent bot updates/messages
- set_webhook: Configure webhook for real-time updates
- get_me: Get bot information

This server acts as a bridge between Jev AI and Telegram.
"""

import asyncio
import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import structlog
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = structlog.get_logger()

# Server configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8765"))
DEFAULT_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Global state
_message_queue = asyncio.Queue()
_bot: Optional[Bot] = None
_dp: Optional[Dispatcher] = None
_web_app: Optional[web.Application] = None


# ============================================
# TELEGRAM BOT HANDLERS
# ============================================

async def cmd_start(message: Message) -> None:
    """Handle /start command"""
    await message.answer(
        "👋 *Jev AI Telegram MCP Server*\n\n"
        "Bot is connected and ready to receive commands.\n\n"
        "Commands:\n"
        "/start - Initialize bot\n"
        "/ping - Check connectivity\n"
        "/help - Show help",
        parse_mode="Markdown"
    )
    logger.info("User started bot", chat_id=message.chat.id)


async def cmd_ping(message: Message) -> None:
    """Handle /ping command"""
    await message.answer("🟢 Bot is online")
    logger.info("Ping received", chat_id=message.chat.id)


async def cmd_help(message: Message) -> None:
    """Handle /help command"""
    await message.answer(
        "📚 *Jev AI MCP Server Help*\n\n"
        "This bot is part of the Jev AI copy trading system.\n\n"
        "Available commands:\n"
        "/start - Initialize bot\n"
        "/ping - Check connectivity\n"
        "/help - Show this message\n\n"
        "For trading commands, use the main Jev AI bot.",
        parse_mode="Markdown"
    )


async def message_handler(message: Message) -> None:
    """Handle all other messages"""
    # Add to message queue for MCP retrieval
    await _message_queue.put({
        "chat_id": message.chat.id,
        "text": message.text,
        "from_user": message.from_user.username if message.from_user else "unknown",
        "timestamp": datetime.utcnow().isoformat(),
    })
    logger.info("Message received", chat_id=message.chat.id, text=message.text)


# ============================================
# MCP TOOL HANDLERS
# ============================================

async def send_message(chat_id: str, text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
    """Send a message to Telegram"""
    if not _bot:
        return {"success": False, "error": "Bot not initialized"}
    
    try:
        await _bot.send_message(
            chat_id=chat_id or DEFAULT_CHAT_ID,
            text=text,
            parse_mode=parse_mode,
        )
        logger.info("Message sent", chat_id=chat_id)
        return {"success": True, "chat_id": chat_id}
    except Exception as e:
        logger.error("Failed to send message", error=str(e))
        return {"success": False, "error": str(e)}


async def get_updates(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent messages from queue"""
    messages = []
    for _ in range(min(limit, _message_queue.qsize())):
        try:
            msg = _message_queue.get_nowait()
            messages.append(msg)
        except asyncio.QueueEmpty:
            break
    return messages


async def set_webhook(url: str) -> Dict[str, Any]:
    """Set Telegram webhook"""
    if not _bot:
        return {"success": False, "error": "Bot not initialized"}
    
    try:
        await _bot.set_webhook(url=url)
        logger.info("Webhook set", url=url)
        return {"success": True, "url": url}
    except Exception as e:
        logger.error("Failed to set webhook", error=str(e))
        return {"success": False, "error": str(e)}


async def get_me() -> Dict[str, Any]:
    """Get bot information"""
    if not _bot:
        return {"success": False, "error": "Bot not initialized"}
    
    try:
        me = await _bot.get_me()
        return {
            "success": True,
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "is_bot": me.is_bot,
        }
    except Exception as e:
        logger.error("Failed to get bot info", error=str(e))
        return {"success": False, "error": str(e)}


# ============================================
# HTTP SERVER FOR MCP
# ============================================

async def handle_mcp(request: web.Request) -> web.Response:
    """Handle MCP tool calls"""
    try:
        data = await request.json()
        method = data.get("method")
        params = data.get("params", {})
        
        logger.info("MCP request", method=method)
        
        result = None
        
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "send_message":
                result = await send_message(
                    chat_id=arguments.get("chat_id", DEFAULT_CHAT_ID),
                    text=arguments.get("text", ""),
                    parse_mode=arguments.get("parse_mode", "Markdown"),
                )
            elif tool_name == "get_updates":
                result = await get_updates(
                    limit=arguments.get("limit", 10),
                )
            elif tool_name == "set_webhook":
                result = await set_webhook(
                    url=arguments.get("url", ""),
                )
            elif tool_name == "get_me":
                result = await get_me()
            else:
                result = {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        return web.json_response({
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "result": {"content": [result]},
        })
        
    except Exception as e:
        logger.error("MCP request failed", error=str(e))
        return web.json_response({
            "jsonrpc": "2.0",
            "id": data.get("id") if 'data' in locals() else None,
            "error": {"code": -32603, "message": str(e)},
        }, status=500)


async def handle_health(request: web.Request) -> web.Response:
    """Health check endpoint"""
    return web.json_response({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})


async def handle_webhook(request: web.Request) -> web.Response:
    """Handle Telegram webhook updates"""
    try:
        update = await request.json()
        await _dp.feed_update(_bot, types.Update(**update))
        return web.json_response({"ok": True})
    except Exception as e:
        logger.error("Webhook update failed", error=str(e))
        return web.json_response({"ok": False, "error": str(e)}, status=500)


# ============================================
# SERVER INITIALIZATION
# ============================================

async def initialize_bot() -> None:
    """Initialize Telegram bot and dispatcher"""
    global _bot, _dp
    
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, bot disabled")
        return
    
    _bot = Bot(token=TELEGRAM_BOT_TOKEN)
    _dp = Dispatcher()
    
    # Register handlers
    _dp.message.register(cmd_start, Command("start"))
    _dp.message.register(cmd_ping, Command("ping"))
    _dp.message.register(cmd_help, Command("help"))
    _dp.message.register(message_handler)
    
    logger.info("Telegram bot initialized", username=(await _bot.get_me()).username)


async def initialize_web_app() -> web.Application:
    """Initialize HTTP server for MCP"""
    global _web_app
    
    app = web.Application()
    app.router.add_post("/mcp", handle_mcp)
    app.router.add_get("/health", handle_health)
    app.router.add_post(f"/webhook/{TELEGRAM_BOT_TOKEN}", handle_webhook) if TELEGRAM_BOT_TOKEN else None
    
    _web_app = app
    return app


async def run_polling() -> None:
    """Run bot polling (alternative to webhook)"""
    if _dp and _bot:
        logger.info("Starting bot polling")
        await _dp.start_polling(_bot)


# ============================================
# MAIN ENTRY POINT
# ============================================

async def main() -> None:
    """Main entry point"""
    logger.info("Starting Telegram MCP Server")
    
    # Initialize components
    await initialize_bot()
    app = await initialize_web_app()
    
    # Start HTTP server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_SERVER_PORT)
    await site.start()
    
    logger.info(f"HTTP server started on port {MCP_SERVER_PORT}")
    
    # Start bot polling in background
    if _dp and _bot:
        asyncio.create_task(run_polling())
    
    # Keep server running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
