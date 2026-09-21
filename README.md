# Jev AI - Polymarket Copy Trading

**Statut actuel :** Prototype de recherche et paper-trading. **Pas d'exé¬¬cution réelle d'ordres.**

## Avertissement

Ce projet est un **outil de recherche et de simulation**. Il ne doit **pas** être utilisé pour trader avec de l'argent réel sans :

- Une validation rigoureuse de l'edge sur données historiques et en paper-trading
- Une infrastructure de sécurité appropriÃ©e (gestion de clÃ©s, rÃ©conciliation, kill switch)
- Une comprÃ©hension complÃ¨te des risques (smart contracts, slippage, liquiditÃ©, rÃ©glementation)

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Wallet Tracker  │────▶│  Copy Executor   │────▶│  Paper Trades   │
│  (MCP Server)   │     │  (Simulation)    │     │   (Database)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│   Telegram UI   │     │   Prometheus     │
│  (Commands)     │     │   (Metrics)      │
└─────────────────┘     └──────────────────┘
```

## FonctionnalitÃ©s

### Tracking de wallets

- Scan pÃ©riodique du leaderboard Polymarket via MCP
- Filtrage par PnL, win rate, volume et nombre de trades
- Persistance dans PostgreSQL

### Copy executor (paper trading)

- Simulation d'exÃ©cution basÃ©e sur les trades rÃ©cents
- ContrÃ´les : liquiditÃ©, duplication, limite de positions
- Journalisation structurÃ©e de chaque signal

### Interface Telegram

- `/whales` : top wallets suivis
- `/positions` : positions ouvertes
- `/pnl` : performance cumulÃ©e

### MÃ©triques

- Nombre de wallets suivis
- Positions ouvertes
- PnL rÃ©alisÃ© et non rÃ©alisÃ©
- Export Prometheus (port 9091)

## DÃ©marrage rapide

```bash
# 1. Cloner
git clone https://github.com/mednabouli/jev-ai-polymarket-copy-trading.git
cd jev-ai-polymarket-copy-trading/jev-ai

# 2. Configurer
cp .env.example .env
# Ãditer .env avec vos paramÃ¨tres (MCP servers, Telegram, etc.)

# 3. Lancer avec Docker Compose
docker compose up -d

# 4. VÃ©rifier les logs
docker compose logs -f jev-ai
```

## Configuration

| Variable | Description | DÃ©faut |
|----------|-------------|--------|
| `ENVIRONMENT` | `development`, `test`, `production` | `development` |
| `DATABASE_URL` | URL PostgreSQL | `postgresql://jev_user:jev_pass@localhost:5432/jev_ai` |
| `MCP_POLYMARKET_URL` | URL serveur MCP Polymarket | `http://localhost:8081` |
| `MCP_TELEGRAM_URL` | URL serveur MCP Telegram | `http://localhost:8082` |
| `POSITION_SIZE_USDC` | Taille de position | `50.0` |
| `MAX_POSITIONS` | Positions max simultanÃ©es | `10` |
| `MIN_TRADES_90D` | Trades min (90j) | `20` |
| `MIN_LIFETIME_PNL` | PnL min USD | `10000.0` |
| `MIN_WIN_RATE` | Win rate min | `0.20` |
| `TELEGRAM_BOT_TOKEN` | Token bot Telegram | (requis en prod) |
| `TELEGRAM_CHAT_ID` | Chat ID Telegram | (requis en prod) |

## Tests

```bash
# Lancer les tests
pytest jev-ai/tests/ -v

# Avec coverage
pytest jev-ai/tests/ --cov=jev-ai --cov-report=term-missing
```

## Roadmap

### Phase 1 - Edge research (actuel)

- [x] Infrastructure de base (DB, MCP, Telegram, mÃ©triques)
- [x] Tests unitaires
- [x] CI/CD
- [ ] Ingestion historique vÃ©rifiÃ©e des trades Polymarket
- [ ] Calcul PnL rÃ©el par wallet
- [ ] DÃ©tection market making / arbitrage
- [ ] Simulation slippage + frais

### Phase 2 - Paper trading rigoureux

- [ ] Event sourcing complet (signals, ordres, fills, rÃ©solutions)
- [ ] Idempotency keys
- [ ] Gestion de position par marchÃ©
- [ ] Limites d'exposition et kill switch
- [ ] Backtest walk-forward

### Phase 3 - ExÃ©cution rÃ©elle limitÃ©e

- [ ] Service de signature isolÃ© (Vault/KMS)
- [ ] Ordres limite post-only
- [ ] RÃ©conciliation continue
- [ ] Alertes anomalies

## SÃ©curitÃ©

- **Ne jamais commiter** `.env` ou clÃ©s privÃ©es
- Utiliser Vault ou secrets managÃ©s en production
- Isoler le wallet de trading du wallet principal
- Activer 2FA sur tous les comptes associÃ©s

## Licence

MIT
