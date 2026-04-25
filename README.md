# Madstreaks Backend

FastAPI server for real-time watchlist alerts, Groww order placement, and Telegram notifications.

## Features

- 📊 **Live Price Monitoring** — Groww WebSocket feed for real-time price ticks
- 🚨 **Instant Alerts** — Fire watchlist alerts when price conditions met (above/below/pct_change)
- 💬 **Telegram Bot** — Send/receive alerts and commands via Telegram
- 📈 **Trade Signals** — Post trade signals to Telegram channel
- 🎯 **Order Management** — Place and track Groww FNO orders

## Tech Stack

- FastAPI + uvicorn (async HTTP server)
- python-telegram-bot v21 (async Telegram bot)
- growwapi (Groww official SDK)
- supabase-py (async Supabase client)
- asyncio (concurrent feed + bot + API)

## Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and fill in credentials:

```bash
cp .env.example .env
```

Required:
- `GROWW_API_KEY` — Groww API key (ES256 JWT)
- `TELEGRAM_BOT_TOKEN` — Bot token from BotFather
- `TELEGRAM_CHAT_ID` — Your personal chat ID (for commands)
- `TELEGRAM_CHANNEL_ID` — Broadcast channel ID (for alerts)
- `SUPABASE_SERVICE_KEY` — Service role key (from Supabase dashboard)

### 2. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 3. Run Locally

```bash
uvicorn app.main:app --reload
```

Server runs on `http://localhost:8000` with docs at `/docs`.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Root |
| GET | `/health` | Server health + feed status |
| GET | `/watchlist` | List all active alerts |
| POST | `/watchlist/refresh` | Force reload alerts |
| GET | `/positions` | Groww open positions |
| POST | `/orders` | Place an order |
| POST | `/signals` | Post trade signal to Telegram |

## Telegram Bot Commands

| Command | Example | What it does |
|---------|---------|-------------|
| `/start` | `/start` | Show help |
| `/watchlist` | `/watchlist` | List active alerts |
| `/add` | `/add NIFTY below 24000` | Add alert |
| `/remove` | `/remove <id>` | Remove alert |
| `/status` | `/status` | Server health |
| `/positions` | `/positions` | Open Groww positions |

## Architecture

```
Groww Feed (WebSocket)
    ↓
Price Ticks
    ↓
AlertManager.check()
    ↓
Notifier.send() → Telegram
    ↓
Update Supabase
```

## Deployment (Railway.app)

1. Create Railway project
2. Connect GitHub repo
3. Set environment variables in Railway dashboard
4. Deploy — Railway auto-runs `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Files

- `app/main.py` — FastAPI app + lifespan
- `app/config.py` — Pydantic settings
- `app/database.py` — Supabase async client
- `app/groww/` — Groww API integration
- `app/telegram/` — Telegram bot setup + handlers
- `app/watchlist/` — Alert checking + notifications
- `app/signals/` — Trade signal posting

## Notes

- Groww feed runs in background asyncio task (non-blocking)
- Telegram bot polls for commands concurrently
- FastAPI HTTP server accepts requests while feed + bot run
- All three run in single process with shared asyncio event loop
