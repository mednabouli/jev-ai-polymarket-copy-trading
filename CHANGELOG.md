# Changelog

All notable changes to Jev AI are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure with Jev AI orchestrator
- Polymarket MCP server with 8 tools (markets, trades, leaderboard, orders)
- Telegram MCP server with messaging and webhook support
- PostgreSQL schema with wallet tracking, copy trades, and PnL tables
- Docker Compose stack for one-command deployment
- Prometheus metrics and Grafana dashboard provisioning
- Professional README.md and landing page (index.html)
- Test suite with pytest fixtures and CI/CD workflow
- CONTRIBUTING.md and CHANGELOG.md documentation

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

---

## [0.1.0] - 2026-09-20

### Added
- Project inception
- Core architecture design
- MCP server implementations
- Wallet filtering logic (90-day profitability thresholds)
- Copy execution with position sizing and liquidity checks
- Telegram bot with 9 commands
- GitHub repository setup

## Legend

- **Added**: New features or capabilities
- **Changed**: Changes in existing functionality
- **Deprecated**: Features marked for future removal
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements
