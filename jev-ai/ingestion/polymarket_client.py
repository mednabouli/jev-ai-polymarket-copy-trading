"""Polymarket Data API client.

Base URL: https://data-api.polymarket.com
No authentication required for public endpoints.
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class PolymarketDataClient:
    """Client for Polymarket Data API v1."""

    BASE_URL = "https://data-api.polymarket.com"

    def __init__(self, timeout: float = 30.0):
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def get_leaderboard(
        self,
        category: str = "OVERALL",
        time_period: str = "DAY",
        order_by: str = "PNL",
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get trader leaderboard rankings.

        Args:
            category: Market category (OVERALL, POLITICS, SPORTS, etc.)
            time_period: DAY, WEEK, MONTH, ALL
            order_by: PNL or VOL
            limit: Max results (1-50)
            offset: Pagination offset (0-1000)

        Returns:
            List of trader entries with rank, proxyWallet, userName, vol, pnl, etc.
        """
        params = {
            "category": category,
            "timePeriod": time_period,
            "orderBy": order_by,
            "limit": min(limit, 50),
            "offset": offset,
        }

        try:
            response = await self._client.get("/v1/leaderboard", params=params)
            response.raise_for_status()
            data = response.json()
            logger.info(
                "Fetched leaderboard",
                category=category,
                time_period=time_period,
                count=len(data),
            )
            return data
        except Exception as e:
            logger.error("Failed to fetch leaderboard", error=str(e))
            return []

    async def get_trades(
        self,
        user: Optional[str] = None,
        market: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get trades for a user or market.

        Args:
            user: Wallet address (0x-prefixed, 40 hex chars)
            market: Condition ID (0x-prefixed, 64 hex chars)
            start_time: Lower bound timestamp (epoch seconds)
            end_time: Upper bound timestamp (epoch seconds)
            limit: Page size (0-10000)
            offset: Starting index (0-10000)

        Returns:
            List of trades with proxyWallet, side, asset, conditionId, size, price, timestamp, etc.
        """
        params = {
            "limit": min(limit, 10000),
            "offset": offset,
            "takerOnly": True,
        }

        if user:
            params["user"] = user
        if market:
            params["market"] = market
        if start_time:
            params["start"] = int(start_time.timestamp())
        if end_time:
            params["end"] = int(end_time.timestamp())

        try:
            response = await self._client.get("/trades", params=params)
            response.raise_for_status()
            data = response.json()
            logger.info(
                "Fetched trades",
                user=user,
                market=market,
                count=len(data),
            )
            return data
        except Exception as e:
            logger.error("Failed to fetch trades", error=str(e))
            return []

    async def get_user_activity(self, user: str) -> Dict[str, Any]:
        """Get on-chain activity for a user.

        Args:
            user: Wallet address (0x-prefixed, 40 hex chars)

        Returns:
            User activity data
        """
        params = {"user": user}

        try:
            response = await self._client.get("/user-activity", params=params)
            response.raise_for_status()
            data = response.json()
            logger.info("Fetched user activity", user=user)
            return data
        except Exception as e:
            logger.error("Failed to fetch user activity", error=str(e))
            return {}

    async def get_current_positions(self, user: str) -> List[Dict[str, Any]]:
        """Get current open positions for a user.

        Args:
            user: Wallet address (0x-prefixed, 40 hex chars)

        Returns:
            List of open positions
        """
        params = {"user": user}

        try:
            response = await self._client.get("/positions", params=params)
            response.raise_for_status()
            data = response.json()
            logger.info("Fetched current positions", user=user)
            return data
        except Exception as e:
            logger.error("Failed to fetch positions", error=str(e))
            return []

    async def get_closed_positions(
        self,
        user: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get closed positions for a user.

        Args:
            user: Wallet address
            start_time: Lower bound timestamp
            end_time: Upper bound timestamp
            limit: Page size
            offset: Starting index

        Returns:
            List of closed positions with PnL data
        """
        params = {
            "user": user,
            "limit": min(limit, 10000),
            "offset": offset,
        }

        if start_time:
            params["start"] = int(start_time.timestamp())
        if end_time:
            params["end"] = int(end_time.timestamp())

        try:
            response = await self._client.get("/closed-positions", params=params)
            response.raise_for_status()
            data = response.json()
            logger.info("Fetched closed positions", user=user, count=len(data))
            return data
        except Exception as e:
            logger.error("Failed to fetch closed positions", error=str(e))
            return []
