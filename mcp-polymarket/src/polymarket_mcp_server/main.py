"""
Polymarket MCP Server

Provides Model Context Protocol tools for accessing Polymarket data:
- get_markets: List markets with filtering
- get_market_by_id: Get market details
- get_order_book: Get order book data
- get_recent_trades: Get recent trades
- get_leaderboard: Get top traders
- get_wallet_trades: Get trades for specific wallets
- get_wallet_stats: Get wallet statistics
- place_order: Execute trades (requires wallet connection)
"""

import asyncio
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import structlog
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = structlog.get_logger()

# Server configuration
GAMMA_API_URL = os.getenv("GAMMA_API_URL", "https://gamma-api.polymarket.com")
GAMMA_REQUIRES_AUTH = os.getenv("GAMMA_REQUIRES_AUTH", "false").lower() == "true"
SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8766"))

# Create MCP server
server = Server("polymarket-mcp")


# ============================================
# TOOL DEFINITIONS
# ============================================

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="get_markets",
            description="Get list of Polymarket markets with filtering options",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 50},
                    "offset": {"type": "integer", "default": 0},
                    "category": {"type": "string"},
                    "min_volume": {"type": "number"},
                    "sort_by": {"type": "string", "enum": ["volume", "liquidity", "expiry"]},
                },
            },
        ),
        Tool(
            name="get_market_by_id",
            description="Get detailed information about a specific market",
            inputSchema={
                "type": "object",
                "properties": {
                    "market_id": {"type": "string"},
                },
                "required": ["market_id"],
            },
        ),
        Tool(
            name="get_order_book",
            description="Get order book for a market",
            inputSchema={
                "type": "object",
                "properties": {
                    "market_id": {"type": "string"},
                },
                "required": ["market_id"],
            },
        ),
        Tool(
            name="get_recent_trades",
            description="Get recent trades for a market or wallet",
            inputSchema={
                "type": "object",
                "properties": {
                    "market_id": {"type": "string"},
                    "wallet_address": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                },
            },
        ),
        Tool(
            name="get_leaderboard",
            description="Get top traders by PnL",
            inputSchema={
                "type": "object",
                "properties": {
                    "timeframe": {"type": "string", "enum": ["24h", "7d", "30d", "90d", "all"]},
                    "min_pnl": {"type": "number", "default": 0},
                    "limit": {"type": "integer", "default": 100},
                },
            },
        ),
        Tool(
            name="get_wallet_trades",
            description="Get trades for specific wallets",
            inputSchema={
                "type": "object",
                "properties": {
                    "wallet_addresses": {"type": "array", "items": {"type": "string"}},
                    "since": {"type": "string", "format": "date-time"},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["wallet_addresses"],
            },
        ),
        Tool(
            name="get_wallet_stats",
            description="Get statistics for a wallet (PnL, win rate, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "wallet_address": {"type": "string"},
                },
                "required": ["wallet_address"],
            },
        ),
        Tool(
            name="place_order",
            description="Place an order on Polymarket (requires wallet connection)",
            inputSchema={
                "type": "object",
                "properties": {
                    "market_id": {"type": "string"},
                    "outcome": {"type": "string"},
                    "side": {"type": "string", "enum": ["YES", "NO"]},
                    "shares": {"type": "number"},
                    "price": {"type": "number"},
                    "order_type": {"type": "string", "enum": ["market", "limit"]},
                },
                "required": ["market_id", "outcome", "side", "shares"],
            },
        ),
    ]


# ============================================
# TOOL HANDLERS
# ============================================

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    logger.info("Tool call", name=name, arguments=arguments)
    
    try:
        if name == "get_markets":
            result = await get_markets(
                limit=arguments.get("limit", 50),
                offset=arguments.get("offset", 0),
                category=arguments.get("category"),
                min_volume=arguments.get("min_volume"),
                sort_by=arguments.get("sort_by", "volume"),
            )
        elif name == "get_market_by_id":
            result = await get_market_by_id(arguments["market_id"])
        elif name == "get_order_book":
            result = await get_order_book(arguments["market_id"])
        elif name == "get_recent_trades":
            result = await get_recent_trades(
                market_id=arguments.get("market_id"),
                wallet_address=arguments.get("wallet_address"),
                limit=arguments.get("limit", 50),
            )
        elif name == "get_leaderboard":
            result = await get_leaderboard(
                timeframe=arguments.get("timeframe", "90d"),
                min_pnl=arguments.get("min_pnl", 0),
                limit=arguments.get("limit", 100),
            )
        elif name == "get_wallet_trades":
            result = await get_wallet_trades(
                wallet_addresses=arguments["wallet_addresses"],
                since=arguments.get("since"),
                limit=arguments.get("limit", 50),
            )
        elif name == "get_wallet_stats":
            result = await get_wallet_stats(arguments["wallet_address"])
        elif name == "place_order":
            result = await place_order(
                market_id=arguments["market_id"],
                outcome=arguments["outcome"],
                side=arguments["side"],
                shares=arguments["shares"],
                price=arguments.get("price"),
                order_type=arguments.get("order_type", "market"),
            )
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        return [TextContent(type="text", text=str(result))]
        
    except Exception as e:
        logger.error("Tool call failed", name=name, error=str(e))
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================
# API CLIENT FUNCTIONS
# ============================================

async def get_markets(
    limit: int = 50,
    offset: int = 0,
    category: Optional[str] = None,
    min_volume: Optional[float] = None,
    sort_by: str = "volume",
) -> Dict[str, Any]:
    """Get list of markets from Gamma API"""
    async with httpx.AsyncClient() as client:
        params = {
            "limit": limit,
            "offset": offset,
            "sort": sort_by,
        }
        if category:
            params["category"] = category
        if min_volume:
            params["min_volume"] = min_volume
        
        response = await client.get(
            f"{GAMMA_API_URL}/markets",
            params=params,
        )
        response.raise_for_status()
        return response.json()


async def get_market_by_id(market_id: str) -> Dict[str, Any]:
    """Get market details"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GAMMA_API_URL}/markets/{market_id}")
        response.raise_for_status()
        return response.json()


async def get_order_book(market_id: str) -> Dict[str, Any]:
    """Get order book for a market"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GAMMA_API_URL}/markets/{market_id}/order-book")
        response.raise_for_status()
        return response.json()


async def get_recent_trades(
    market_id: Optional[str] = None,
    wallet_address: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get recent trades"""
    async with httpx.AsyncClient() as client:
        params = {"limit": limit}
        if market_id:
            params["market_id"] = market_id
        if wallet_address:
            params["wallet"] = wallet_address
        
        response = await client.get(
            f"{GAMMA_API_URL}/trades",
            params=params,
        )
        response.raise_for_status()
        return response.json().get("trades", [])


async def get_leaderboard(
    timeframe: str = "90d",
    min_pnl: float = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get top traders by PnL.
    
    Note: This is a simulated implementation.
    In production, you'd need to aggregate from on-chain data or use a service like PolyTrace.
    """
    # Simulated leaderboard data
    # In production, this would query PolyTrace, Polynyx, or aggregate from chain
    traders = [
        {
            "address": f"0x{'abc123' * 7}",
            "pnl_usd": 66200,
            "trades_90d": 401,
            "win_rate": 0.54,
            "volume_usd": 28700000,
            "crypto_pnl": 45000,
            "politics_pnl": 15000,
            "sports_pnl": 6200,
            "other_pnl": 0,
        },
        {
            "address": f"0x{'def456' * 7}",
            "pnl_usd": 61300,
            "trades_90d": 523,
            "win_rate": 0.48,
            "volume_usd": 49500000,
            "crypto_pnl": 40000,
            "politics_pnl": 20000,
            "sports_pnl": 1300,
            "other_pnl": 0,
        },
        {
            "address": f"0x{'789ghi' * 7}",
            "pnl_usd": 55200,
            "trades_90d": 312,
            "win_rate": 0.51,
            "volume_usd": 28500000,
            "crypto_pnl": 35000,
            "politics_pnl": 18000,
            "sports_pnl": 2200,
            "other_pnl": 0,
        },
    ]
    
    # Filter by min_pnl
    filtered = [t for t in traders if t["pnl_usd"] >= min_pnl]
    
    # Sort by PnL
    filtered.sort(key=lambda x: x["pnl_usd"], reverse=True)
    
    return filtered[:limit]


async def get_wallet_trades(
    wallet_addresses: List[str],
    since: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get trades for specific wallets"""
    async with httpx.AsyncClient() as client:
        params = {
            "wallets": ",".join(wallet_addresses),
            "limit": limit,
        }
        if since:
            params["since"] = since
        
        response = await client.get(
            f"{GAMMA_API_URL}/wallet-trades",
            params=params,
        )
        response.raise_for_status()
        return response.json().get("trades", [])


async def get_wallet_stats(wallet_address: str) -> Dict[str, Any]:
    """Get wallet statistics"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GAMMA_API_URL}/wallets/{wallet_address}/stats"
        )
        response.raise_for_status()
        return response.json()


async def place_order(
    market_id: str,
    outcome: str,
    side: str,
    shares: float,
    price: Optional[float] = None,
    order_type: str = "market",
) -> Dict[str, Any]:
    """
    Place an order on Polymarket.
    
    Note: This requires wallet connection and signature.
    In production, you'd use the Polymarket CLOB client with private key.
    """
    # Simulated order placement
    # In production, this would sign and submit to CLOB
    
    logger.info(
        "Placing order",
        market_id=market_id,
        outcome=outcome,
        side=side,
        shares=shares,
        price=price,
        order_type=order_type,
    )
    
    # Simulated response
    return {
        "success": True,
        "order_id": "simulated_order_123",
        "avg_price": price or 0.5,
        "shares_filled": shares,
        "total_cost": shares * (price or 0.5),
    }


# ============================================
# SERVER ENTRY POINT
# ============================================

async def main():
    """Run the MCP server"""
    logger.info("Starting Polymarket MCP Server")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
