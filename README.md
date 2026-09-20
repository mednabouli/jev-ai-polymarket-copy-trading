# 🚀 Jev AI - Polymarket Copy Trading Automation

> **Automated copy trading for Polymarket prediction markets** — Track profitable whales, execute copy trades in real-time, and monitor PnL via Telegram. Zero API keys required.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=flat&logo=telegram)](https://telegram.org/)

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Telegram Commands](#-telegram-commands)
- [Profitable Wallet Filters](#-profitable-wallet-filters)
- [Project Structure](#-project-structure)
- [Monitoring](#-monitoring)
- [Security](#-security)
- [Development](#-development)
- [License](#-license)

---

## ✨ Features

### 🔍 Smart Wallet Discovery
- **Automated scanning** of 200K+ Polymarket wallets
- **90-day profitability filters** (min 20 trades, $10K+ PnL, 20%+ win rate)
- **Category-specific PnL tracking** (crypto, politics, sports, other)
- **Real-time leaderboard updates** via MCP server

### 🤖 Copy Trading Automation
- **Sub-second trade detection** from followed wallets
- **Configurable position sizing** (fixed USD or Kelly-based)
- **Latency tracking** and optimization
- **Automatic PnL calculation** (realized + unrealized)

### 📱 Telegram Integration
- **Real-time trade alerts** with market context
- **Interactive commands** (`/whales`, `/follow`, `/positions`, `/pnl`)
- **Portfolio monitoring** on-the-go
- **Alert customization** (on/off, min trade size, categories)

### 🔐 Zero API Key Architecture
- **Claude Code OAuth session** authentication (no API key needed)
- **Local MCP servers** (HTTP transport, localhost only)
- **Environment-based secrets** (no hardcoded credentials)

### 📊 Observability
- **Prometheus metrics** (copy trades, PnL, latency, wallet counts)
- **Grafana dashboards** (pre-configured panels)
- **Structured logging** (JSON format, log levels)
- **PostgreSQL persistence** (full audit trail)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Local Machine / VPS                      │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  Claude Code │    │   Jev AI     │    │  Telegram Bot    │   │
│  │   Session    │───▶│   Orchestrator│───▶│   (aiogram)      │   │
│  │  (OAuth)     │    │   (Python)   │    │                  │   │
│  └──────────────┘    └──────────────┘    └──────────────────┘   │
│         │                   │                      │             │
│         ▼                   ▼                      ▼             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   MCP        │    │  Polymarket  │    │   Your Telegram  │   │
│  │  Server      │    │   MCP        │    │   Chat           │   │
│  │  (Telegram)  │    │   Server     │    │                  │   │
│  └──────────────┘    └──────────────┘    └──────────────────┘   │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  PostgreSQL  │    │  Prometheus  │    │    Grafana       │   │
│  │   Database   │    │   Metrics    │    │   Dashboards     │   │
│  └──────────────┘    └──────────────┘    └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Jev AI Orchestrator** | Python 3.11 + asyncio | Main automation logic |
| **Polymarket MCP Server** | MCP protocol + Gamma API | Market data, whale tracking |
| **Telegram MCP Server** | aiogram + MCP | Bidirectional messaging |
| **Database** | PostgreSQL 17 | Trade history, PnL, config |
| **Metrics** | Prometheus + Grafana | Monitoring and alerting |

---

## 🚀 Quick Start

### Prerequisites

- **Docker** 24+ and **Docker Compose** 2.20+
- **Python** 3.11+ (for local development)
- **Claude Code** CLI installed and authenticated
- **Telegram** account (for bot creation)

### Step 1: Clone the Repository

```bash
git clone https://github.com/mednabouli/jev-ai-polymarket-copy-trading.git
cd jev-ai-polymarket-copy-trading
```

### Step 2: Configure Environment

```bash
cp env.env .env
```

Edit `.env` with your settings:

```env
# Claude Code Session (REQUIRED)
CLAUDE_CODE_OAUTH_TOKEN=your_session_token_here

# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=your_chat_id

# Copy Trading Rules
MIN_TRADES_90D=20
MIN_LIFETIME_PNL=10000
MIN_WIN_RATE=0.20
MAX_POSITIONS=10
POSITION_SIZE_USDC=50
```

### Step 3: Get Claude Code Session Token

```bash
# Authenticate with Claude Code
claude /login

# Export the session token
export CLAUDE_CODE_OAUTH_TOKEN=$(claude --show-session-token)
```

### Step 4: Create Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow prompts
3. Copy the bot token to `.env`
4. Send `/start` to your new bot to get chat ID

### Step 5: Start All Services

```bash
docker compose up -d
```

### Step 6: Verify Deployment

```bash
# Check logs
docker compose logs -f jev-ai

# Check metrics
open http://localhost:9090

# Check Grafana
open http://localhost:3000  # admin/admin
```

### Step 7: Test Telegram Bot

Send these commands to your bot:

```
/start      # Initialize
/whales     # View top wallets
/help       # Show all commands
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | ✅ | - | Claude Code OAuth session token |
| `TELEGRAM_BOT_TOKEN` | ✅ | - | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | - | Your Telegram chat ID |
| `MIN_TRADES_90D` | ❌ | `20` | Minimum trades in last 90 days |
| `MIN_LIFETIME_PNL` | ❌ | `10000` | Minimum lifetime PnL in USD |
| `MIN_WIN_RATE` | ❌ | `0.20` | Minimum win rate (0.0-1.0) |
| `MAX_POSITIONS` | ❌ | `10` | Maximum simultaneous positions |
| `POSITION_SIZE_USDC` | ❌ | `50` | Position size per copy trade |
| `COPY_SELLS` | ❌ | `true` | Whether to copy sell/exits |
| `POLL_INTERVAL_SECS` | ❌ | `60` | Poll interval for whale trades |

### Copy Trading Rules

The system uses these filters to identify profitable wallets:

1. **Trade Frequency**: Minimum 20 resolved trades in 90 days
2. **Profitability**: Minimum $10,000 lifetime realized PnL
3. **Win Rate**: Minimum 20% win rate (filters lucky one-hits)
4. **Position Limits**: Maximum 10 simultaneous copy positions
5. **Size Control**: Fixed $50 USDC per position (configurable)

---

## 📱 Telegram Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot, show status | `/start` |
| `/whales` | List top profitable wallets | `/whales` |
| `/follow` | Start following a wallet | `/follow 0xabc...123` |
| `/unfollow` | Stop following a wallet | `/unfollow 0xabc...123` |
| `/positions` | View open copy trades | `/positions` |
| `/pnl` | View PnL breakdown | `/pnl` |
| `/alerts` | Toggle trade alerts | `/alerts on` |
| `/config` | Show current configuration | `/config` |
| `/help` | Show all commands | `/help` |

---

## 🎯 Profitable Wallet Filters

Based on analysis of 27K+ Polymarket wallets (June-July 2026):

| Filter | Threshold | Rationale |
|--------|-----------|-----------|
| **90-Day Trades** | ≥20 | 66% profitable vs 12% for one-trade wallets |
| **Lifetime PnL** | ≥$10K | Filters out lucky streaks |
| **Win Rate** | ≥20% | 96-100% profitable above this threshold |
| **Market Breadth** | 4-10 markets | 61% profitable vs 20% for single-market |
| **Position Type** | Opens/adds only | Exits don't signal conviction |

**Source**: [Vultax Research](https://vultax.com/research/best-polymarket-traders-leaderboards), [PolyTrace](https://polytrace.app/)

---

## 📁 Project Structure

```
jev-ai-polymarket-copy-trading/
├── docker-compose.yml          # Main Docker Compose config
├── env.env                     # Environment template
├── README.md                   # This file
├── index.html                  # Landing page
│
├── jev-ai/                     # Main orchestrator
│   ├── Dockerfile
│   ├── main.py                 # Entry point
│   ├── config.py               # Settings loader
│   ├── wallet_tracker.py       # Profitable wallet scanner
│   ├── copy_executor.py        # Trade execution logic
│   ├── telegram_handler.py     # Telegram bot commands
│   ├── database.py             # PostgreSQL wrapper
│   ├── metrics.py              # Prometheus metrics
│   └── requirements.txt        # Python dependencies
│
├── mcp-polymarket/             # Polymarket MCP server
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── src/
│       └── polymarket_mcp_server/
│           └── main.py         # MCP tool handlers
│
├── mcp-telegram/               # Telegram MCP server
│   ├── Dockerfile
│   └── server.py               # aiogram bot + MCP
│
├── postgres/                   # Database initialization
│   └── init.sql                # Schema + views
│
└── monitoring/                 # Observability stack
    ├── prometheus.yml          # Prometheus config
    └── grafana/
        ├── dashboards/         # Pre-configured dashboards
        └── datasources/        # Prometheus datasource
```

---

## 📊 Monitoring

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `copy_trades_total` | Counter | Total copy trades executed |
| `copy_trades_pnl_usd` | Gauge | Current PnL (realized/unrealized) |
| `followed_wallets_count` | Gauge | Number of followed wallets |
| `open_positions_count` | Gauge | Number of open positions |
| `copy_latency_seconds` | Histogram | Trade execution latency |
| `wallet_pnl_usd` | Gauge | PnL per wallet |

### Grafana Dashboards

Access at `http://localhost:3000` (admin/admin):

1. **Overview** - Total PnL, open positions, win rate
2. **Wallet Performance** - Per-wallet PnL, trade count, win rate
3. **Copy Trade Analytics** - Latency, position sizing, category breakdown
4. **System Health** - CPU, memory, database connections

---

## 🔒 Security

### Best Practices

- **Never commit `.env`** - Add to `.gitignore`
- **Use private repo** for production deployments
- **Rotate tokens** every 90 days
- **Limit database access** to localhost only
- **Enable TLS** for production Telegram webhooks

### Architecture Security

| Component | Security Measure |
|-----------|------------------|
| **MCP Servers** | Localhost-only HTTP (no external exposure) |
| **Database** | Password-protected, no remote access |
| **Telegram** | Bot token in environment only |
| **Claude Code** | Session token never leaves machine |

---

## 🛠️ Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r jev-ai/requirements.txt

# Run locally (without Docker)
python jev-ai/main.py
```

### Running Tests

```bash
# Install test dependencies
pip install -r jev-ai/requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest jev-ai/tests/ -v --cov=jev-ai
```

### Building Docker Images

```bash
# Build all images
docker compose build

# Build specific service
docker compose build jev-ai
```

### Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
docker compose up -d

# View logs
docker compose logs -f jev-ai
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Polymarket](https://polymarket.com/) - Prediction market platform
- [PolyTrace](https://polytrace.app/) - Wallet analytics
- [Polynyx](https://www.polynyx.app/) - Smart money tracker
- [Vultax Research](https://vultax.com/research/) - Profitability analysis

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/mednabouli/jev-ai-polymarket-copy-trading/issues)
- **Telegram**: [@jev_ai_support](https://t.me/jev_ai_support) (coming soon)

---

**Built with ❤️ by mednabouli** | [View on GitHub](https://github.com/mednabouli/jev-ai-polymarket-copy-trading)