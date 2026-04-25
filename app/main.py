import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# ============ TRADES CRUD ============

@app.get("/trades")
async def list_trades(user_id: str = None):
    try:
        if user_id:
            response = db.client.table("trades").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        else:
            response = db.client.table("trades").select("*").order("created_at", desc=True).execute()
        return {"trades": response.data}
    except Exception as e:
        logger.error(f"Error listing trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trades")
async def create_trade(trade_data: dict):
    try:
        db.client.table("trades").insert(trade_data).execute()
        return {"status": "created"}
    except Exception as e:
        logger.error(f"Error creating trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trades/{trade_id}")
async def get_trade(trade_id: str):
    try:
        response = db.client.table("trades").select("*").eq("id", trade_id).single().execute()
        return {"trade": response.data}
    except Exception as e:
        logger.error(f"Error fetching trade: {e}")
        raise HTTPException(status_code=404, detail="Trade not found")


@app.put("/trades/{trade_id}")
async def update_trade(trade_id: str, updates: dict):
    try:
        db.client.table("trades").update(updates).eq("id", trade_id).execute()
        return {"status": "updated"}
    except Exception as e:
        logger.error(f"Error updating trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/trades/{trade_id}")
async def delete_trade(trade_id: str):
    try:
        db.client.table("trades").delete().eq("id", trade_id).execute()
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trades/{trade_id}/close")
async def close_trade(trade_id: str, exit_price: float, pnl: float, status: str = "closed"):
    try:
        db.client.table("trades").update({
            "exit_price": exit_price,
            "pnl": pnl,
            "status": status
        }).eq("id", trade_id).execute()
        return {"status": "closed"}
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ WATCHLIST ALERTS CRUD ============

@app.get("/alerts")
async def list_alerts(user_id: str = None, active_only: bool = True):
    try:
        query = db.client.table("watchlist_alerts").select("*")
        if user_id:
            query = query.eq("user_id", user_id)
        if active_only:
            query = query.eq("is_active", True)
        response = query.order("created_at", desc=True).execute()
        return {"alerts": response.data}
    except Exception as e:
        logger.error(f"Error listing alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts")
async def create_alert(alert_data: dict):
    try:
        db.client.table("watchlist_alerts").insert(alert_data).execute()
        await feed_manager.refresh_symbols()
        return {"status": "created"}
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    try:
        response = db.client.table("watchlist_alerts").select("*").eq("id", alert_id).single().execute()
        return {"alert": response.data}
    except Exception as e:
        logger.error(f"Error fetching alert: {e}")
        raise HTTPException(status_code=404, detail="Alert not found")


@app.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, updates: dict):
    try:
        db.client.table("watchlist_alerts").update(updates).eq("id", alert_id).execute()
        await feed_manager.refresh_symbols()
        return {"status": "updated"}
    except Exception as e:
        logger.error(f"Error updating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    try:
        db.client.table("watchlist_alerts").delete().eq("id", alert_id).execute()
        await feed_manager.refresh_symbols()
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/{alert_id}/reset")
async def reset_alert(alert_id: str):
    try:
        db.client.table("watchlist_alerts").update({
            "alert_triggered": False,
            "alert_sent_at": None
        }).eq("id", alert_id).execute()
        return {"status": "reset"}
    except Exception as e:
        logger.error(f"Error resetting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/{alert_id}/toggle")
async def toggle_alert(alert_id: str):
    try:
        alert = await db.get_alert_by_id(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        db.client.table("watchlist_alerts").update({
            "is_active": not alert.get("is_active")
        }).eq("id", alert_id).execute()
        await feed_manager.refresh_symbols()
        return {"status": "toggled", "is_active": not alert.get("is_active")}
    except Exception as e:
        logger.error(f"Error toggling alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ BRIEFING-TO-ALERTS INTEGRATION ============

@app.post("/alerts/from-briefing")
async def create_alerts_from_briefing(
    alerts_data: list[dict],
    user_id: str = "2d620133-08e5-49c1-ae8b-94e85adf29b1",
    authorization: str = Header(None)
):
    """
    Create multiple alerts from briefing research.
    Used by nse-briefing, stock-briefing to add alerts for key levels.

    **Authentication:** Pass API key in Authorization header
    Example: Authorization: Bearer sk-briefing-xxx

    Expected format:
    [
        {
            "symbol": "NIFTY",
            "alert_type": "above",          # above, below, pct_change
            "target_price": 24500,
            "description": "Breakout level",
            "notes": "Expected to reach 25000 if breakout confirmed"
        },
        ...
    ]
    """
    # Validate API key
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # Extract token from "Bearer sk-briefing-xxx"
    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format. Use: Bearer <api-key>")

    api_key = parts[1]
    if api_key != settings.briefing_api_key:
        logger.warning(f"Invalid briefing API key attempted: {api_key[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid API key")

    logger.info(f"Briefing API authenticated - creating {len(alerts_data)} alerts")

    try:
        created = []
        skipped = []

        for alert_data in alerts_data:
            symbol = alert_data.get("symbol")
            alert_type = alert_data.get("alert_type")
            target_price = alert_data.get("target_price")
            description = alert_data.get("description", "")
            notes = alert_data.get("notes", "")

            # Validate required fields
            if not all([symbol, alert_type, target_price is not None]):
                skipped.append({"alert": alert_data, "reason": "missing required fields"})
                continue

            if alert_type not in ["above", "below", "pct_change"]:
                skipped.append({"alert": alert_data, "reason": f"invalid alert_type: {alert_type}"})
                continue

            # Create alert in Supabase
            try:
                alert_record = {
                    "user_id": user_id,
                    "symbol": symbol,
                    "alert_type": alert_type,
                    "target_price": float(target_price),
                    "is_active": True,
                    "notify_telegram": True,
                    "repeat_mode": "one_shot",
                    "notes": f"{description} — {notes}" if description else notes,
                }
                db.client.table("watchlist_alerts").insert(alert_record).execute()
                created.append({"symbol": symbol, "alert_type": alert_type, "target_price": target_price})
                logger.info(f"Alert created from briefing: {symbol} {alert_type} {target_price}")
            except Exception as e:
                skipped.append({"alert": alert_data, "reason": str(e)})

        # Refresh feed with new symbols
        if created:
            await feed_manager.refresh_symbols()

        return {
            "status": "completed",
            "created": created,
            "skipped": skipped,
            "total": len(created) + len(skipped)
        }
    except Exception as e:
        logger.error(f"Error creating alerts from briefing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
