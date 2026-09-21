# Jev AI - Polymarket Copy Trading

**Statut actuel :** Plateforme de paper-trading event-sourced avec scoring de wallets et simulation réaliste.

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
                                │
                                ▼
                       ┌──────────────────┐
                       │    Grafana       │
                       │   (Dashboards)   │
                       └──────────────────┘
```

## FonctionnalitÃ©s

### Ingestion Polymarket

- Scan pÃ©riodique du leaderboard via API Data (`data-api.polymarket.com`)
- Historisation des trades, positions clÃ´turÃ©es, mÃ©triques par wallet
- CatÃ©gories : POLITICS, SPORTS, CRYPTO, OVERALL
- PÃ©riodes : DAY, WEEK, MONTH

### Scoring de wallets

- DÃ©tection **Market Makers** (buy_ratio ~50%, win rate 45-55%,高频)
- DÃ©tection **Arbitrageurs** (win rate >85%, petit PnL, faible variance)
- DÃ©tection **HFT** (>50 trades/jour, nombreux marchÃ©s)
- Score de **copiabilitÃ©** (0-100) : pattern + performance + consistency + activity
- Recommandations : `STRONG BUY`, `BUY`, `HOLD`, `WEAK`, `AVOID`

### Copy executor (paper trading)

- Simulation d'exÃ©cution avec :
  - **Slippage** modÃ©lisÃ© (order book ou estimation)
  - **Frais** Polymarket (2%)
  - **Latence** signal â exÃ©cution
- DÃ©cision go/no-go basÃ©e sur score, liquiditÃ©, fraÃ®cheur du signal
- Event sourcing complet pour audit et replay

### Event sourcing

- **Immutable event log** : `signal_detected`, `execution_decided`, `paper_order_created`, `paper_order_filled`
- **Projections** : `signals`, `paper_orders`, `fills`, `copy_trades`, `market_resolutions`
- **Idempotence** : clÃ©s uniques, pas de replay accidentel
- **Correlation ID** : trace end-to-end d'un trade

### Interface Telegram

- `/whales` : top wallets suivis (triÃ©s par score)
- `/positions` : positions ouvertes
- `/pnl` : performance cumulÃ©e

### Monitoring

- **Prometheus** : mÃ©triques temps rÃ©el (PnL, positions, wallets)
- **Grafana** : dashboard prÃ©-configurÃ© avec 6 panels
  - Followed Wallets
  - Open Positions
  - Realized/Unrealized PnL
  - PnL Over Time
  - Wallets & Positions

## DÃ©marrage rapide

### Option 1 : Docker Compose (recommandÃ©)

```bash
# 1. Cloner
git clone https://github.com/mednabouli/jev-ai-polymarket-copy-trading.git
cd jev-ai-polymarket-copy-trading/jev-ai

# 2. Configurer
cp .env.example .env
# Ãditer .env avec vos paramÃ¨tres (Telegram, etc.)

# 3. Lancer toute la stack
docker compose up -d

# 4. VÃ©rifier les logs
docker compose logs -f jev-ai

# 5. AccÃ©der aux services
# - Grafana : http://localhost:3000 (admin/admin123)
# - Prometheus : http://localhost:9090
# - PostgreSQL : localhost:5432
```

### Option 2 : Manuel

```bash
# 1. Installer les dÃ©pendances
pip install -r requirements.txt

# 2. Configurer
cp .env.example .env

# 3. Lancer PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_USER=jev_user \
  -e POSTGRES_PASSWORD=jev_pass \
  -e POSTGRES_DB=jev_ai \
  -p 5432:5432 \
  postgres:15-alpine

# 4. Lancer l'application
python main.py
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

## Scripts CLI

### Lister les signaux rÃ©cents

```bash
python scripts/list_signals.py --limit 50 --status approved
```

Filtres disponibles :
- `--limit` : nombre max de signaux
- `--status` : `detected`, `approved`, `rejected`
- `--wallet` : filtre par adresse
- `--market` : filtre par ID de marchÃ©

### Auditer un signal spÃ©cifique

```bash
python scripts/replay_signal.py <signal_id>
```

Affiche :
- MÃ©tadatas du signal (wallet, marchÃ©, score, liquiditÃ©)
- Timeline complÃ¨te des Ã ©vÃ©nements
- DÃ©tails de l'ordre paper et du fill
- PnL estimÃ© si position clÃ´turÃ©e

### Rejouer les derniers signaux

```bash
python scripts/replay_recent.py 5
```

Rejoue les 5 derniers signaux avec audit complet.

## Tests

```bash
# Lancer les tests
pytest jev-ai/tests/ -v

# Avec coverage
pytest jev-ai/tests/ --cov=jev-ai --cov-report=term-missing
```

## Roadmap

### Phase 1 - Edge research (â¨½)

- [x] Infrastructure de base (DB, MCP, Telegram, mÃ©triques)
- [x] Tests unitaires
- [x] CI/CD
- [x] Ingestion API Polymarket vÃ©rifiÃ©e
- [x] Calcul PnL par wallet
- [x] DÃ©tection market making / arbitrage / HFT
- [x] Simulation slippage + frais
- [x] Event sourcing complet
- [x] Dashboard Grafana

### Phase 2 - Paper trading rigoureux (en cours)

- [x] Event sourcing complet (signals, ordres, fills, rÃ©solutions)
- [x] Idempotency keys
- [ ] Gestion de position par marchÃ©
- [ ] Limites d'exposition et kill switch
- [ ] Backtest walk-forward
- [ ] Dashboard Grafana avancÃ© (PnL par wallet, catÃ©gorie)

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
