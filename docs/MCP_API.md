# Jev AI MCP API Reference

Jev AI exposes `polymarket` and `telegram` Model Context Protocol services. Calls use JSON-RPC 2.0. The project is a research/paper-trading foundation: `place_order` is currently simulated.

## Request shape

```json
{"jsonrpc":"2.0","id":"request-1","method":"tools/call","params":{"name":"get_markets","arguments":{"limit":10}}}
```

## Polymarket tools

| Tool | Required arguments | Purpose |
|---|---|---|
| `get_markets` | None | List markets; accepts `limit`, `offset`, `category`, `min_volume`, `sort_by` |
| `get_market_by_id` | `market_id` | Read market details |
| `get_order_book` | `market_id` | Read order-book data |
| `get_recent_trades` | None | Read recent trades; accepts `market_id`, `wallet_address`, `limit` |
| `get_leaderboard` | None | Read rankings; accepts `timeframe`, `min_pnl`, `limit`; currently simulated |
| `get_wallet_trades` | `wallet_addresses` | Read wallet trades; accepts `since`, `limit` |
| `get_wallet_stats` | `wallet_address` | Read wallet metrics |
| `place_order` | `market_id`, `outcome`, `side`, `shares` | Simulates an order; not live execution |

## Telegram tools

| Tool | Required arguments | Purpose |
|---|---|---|
| `send_message` | `text` | Sends a message; accepts `chat_id`, `parse_mode` |
| `get_updates` | None | Reads in-memory queued updates; accepts `limit` |
| `set_webhook` | `url` | Configures a Telegram webhook; require HTTPS |
| `get_me` | None | Reads configured bot metadata |

## Security notes

- Keep MCP endpoints private; do not expose them directly to the Internet.
- Put authentication and authorization in front of any remote gateway.
- The Telegram update queue is in memory and non-durable.
- Validate upstream data formats before automating decisions.
