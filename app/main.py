import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings, logger
from app.database import db
from app.groww.feed import FeedManager
from app.telegram.bot import telegram_bot
from app.watchlist.manager import AlertManager
from app.watchlist.notifier import Notifier
from app.signals.generator import SignalGenerator
from app.groww.orders import place_order, get_positions


notifier = Notifier(telegram_bot)
alert_manager = AlertManager(notifier)
signal_generator = SignalGenerator(telegram_bot)
feed_manager = FeedManager(alert_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting madstreaks-backend")

    try:
        await telegram_bot.start()
        logger.info("✅ Telegram bot started")
    except Exception as e:
        logger.error(f"❌ Failed to start Telegram bot: {e}")

    try:
        await feed_manager.start()
        logger.info("✅ Groww feed started")
    except Exception as e:
        logger.error(f"❌ Failed to start Groww feed: {e}")

    yield

    logger.info("🛑 Shutting down")
    await feed_manager.stop()
    await telegram_bot.stop()
    logger.info("✅ Shutdown complete")


app = FastAPI(title="Madstreaks Backend", version="1.0.0", lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Madstreaks backend is running", "version": "1.0.0"}


@app.get("/health")
async def health():
    alerts = await db.get_active_alerts()
    return {
        "status": "ok",
        "feed_running": feed_manager.is_running,
        "active_alerts": len([a for a in alerts if not a.get("alert_triggered")]),
        "triggered_alerts": len([a for a in alerts if a.get("alert_triggered")]),
    }


@app.get("/watchlist")
async def get_watchlist():
    alerts = await db.get_active_alerts()
    return {
        "alerts": alerts,
        "count": len(alerts),
        "active": len([a for a in alerts if not a.get("alert_triggered")]),
        "triggered": len([a for a in alerts if a.get("alert_triggered")]),
    }


@app.post("/watchlist/refresh")
async def refresh_watchlist():
    try:
        await feed_manager.refresh_symbols()
        return {"status": "refreshed"}
    except Exception as e:
        logger.error(f"Error refreshing watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/positions")
async def get_open_positions():
    try:
        positions = await get_positions()
        return {"positions": positions}
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orders")
async def create_order(symbol: str, qty: int, price: float, order_type: str = "BUY"):
    try:
        result = await place_order(symbol, qty, price, order_type)
        return {"order": result}
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/signals")
async def post_signal(symbol: str, direction: str, entry: float, target: float, stop_loss: float):
    try:
        await signal_generator.post_signal(symbol, direction, entry, target, stop_loss)
        return {"status": "signal_posted"}
    except Exception as e:
        logger.error(f"Error posting signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
