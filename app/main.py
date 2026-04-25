import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Depends
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
from app.schemas import TradeCreate, TradeUpdate, AlertCreate, AlertUpdate, BriefingAlert, LoginRequest, SignupRequest
from app.auth import verify_user_token, verify_briefing_api_key


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
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:3000",
        "https://madstreaks.vercel.app",  # TODO: Update with your exact domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Madstreaks backend is running", "version": "1.0.0"}


@app.get("/auth/debug")
async def auth_debug():
    """Debug endpoint - tests JWT decoding with a real token."""
    return {
        "status": "ok",
        "message": "POST a JSON with 'token' field to test JWT decoding",
        "example": {"token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9..."}
    }


@app.post("/auth/debug")
async def auth_debug_token(body: dict):
    """Debug JWT token decoding."""
    token = body.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing 'token' field")

    try:
        import json
        import base64

        token_parts = token.split(".")
        if len(token_parts) != 3:
            return {"error": f"Token has {len(token_parts)} parts instead of 3"}

        payload_part = token_parts[1]
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += "=" * padding

        decoded_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(decoded_bytes)

        return {
            "status": "✅ Decoded successfully",
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "exp": payload.get("exp"),
            "all_claims": list(payload.keys())
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}


# ============ AUTH ENDPOINTS (BACKEND-DRIVEN) ============

@app.post("/auth/login")
async def backend_login(credentials: LoginRequest):
    """
    Backend login endpoint for debugging.
    Frontend currently calls Supabase directly — this is for testing/fallback.
    """
    try:
        response = db.client.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })

        if hasattr(response, 'user') and response.user:
            user = response.user
            return {
                "status": "success",
                "user_id": user.id,
                "email": user.email,
                "message": "Login successful"
            }
        else:
            logger.error(f"Unexpected response format: {response}")
            raise HTTPException(status_code=500, detail="Unexpected auth response")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Login error: {error_msg}")

        if "invalid login credentials" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid email or password")
        elif "email not confirmed" in error_msg.lower():
            raise HTTPException(status_code=403, detail="Email confirmation required — check your inbox")
        elif "400" in error_msg:
            raise HTTPException(status_code=400, detail=f"Supabase error: {error_msg}")
        else:
            raise HTTPException(status_code=500, detail=f"Auth error: {error_msg}")


@app.post("/auth/signup")
async def backend_signup(credentials: SignupRequest):
    """
    Backend signup endpoint for debugging.
    Frontend currently calls Supabase directly — this is for testing/fallback.
    """
    try:
        response = db.client.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password
        })

        if hasattr(response, 'user') and response.user:
            user = response.user
            logger.info(f"User signed up: {user.email}")
            return {
                "status": "success",
                "user_id": user.id,
                "email": user.email,
                "message": "Account created successfully"
            }
        else:
            logger.error(f"Unexpected response format: {response}")
            raise HTTPException(status_code=500, detail="Unexpected auth response")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Signup error: {error_msg}")

        if "already registered" in error_msg.lower():
            raise HTTPException(status_code=409, detail="Email already registered")
        else:
            raise HTTPException(status_code=400, detail=f"Signup error: {error_msg}")


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
async def create_trade(
    trade: TradeCreate,
    user_id: str = Depends(verify_user_token)
):
    try:
        trade_data = trade.dict()
        trade_data["user_id"] = user_id
        db.client.table("trades").insert(trade_data).execute()
        logger.info(f"Trade created for user {user_id}: {trade.symbol}")
        return {"status": "created"}
    except Exception as e:
        logger.error(f"Error creating trade: {e}")
        raise HTTPException(status_code=500, detail="Failed to create trade")


@app.get("/trades/{trade_id}")
async def get_trade(trade_id: str):
    try:
        response = db.client.table("trades").select("*").eq("id", trade_id).single().execute()
        return {"trade": response.data}
    except Exception as e:
        logger.error(f"Error fetching trade: {e}")
        raise HTTPException(status_code=404, detail="Trade not found")


@app.put("/trades/{trade_id}")
async def update_trade(
    trade_id: str,
    updates: TradeUpdate,
    user_id: str = Depends(verify_user_token)
):
    try:
        update_data = updates.dict(exclude_unset=True)
        db.client.table("trades").update(update_data).eq("id", trade_id).eq("user_id", user_id).execute()
        logger.info(f"Trade updated for user {user_id}: {trade_id}")
        return {"status": "updated"}
    except Exception as e:
        logger.error(f"Error updating trade: {e}")
        raise HTTPException(status_code=500, detail="Failed to update trade")


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
async def create_alert(
    alert: AlertCreate,
    user_id: str = Depends(verify_user_token)
):
    try:
        alert_data = alert.dict()
        alert_data["user_id"] = user_id
        db.client.table("watchlist_alerts").insert(alert_data).execute()
        await feed_manager.refresh_symbols()
        logger.info(f"Alert created for user {user_id}: {alert.symbol}")
        return {"status": "created"}
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alert")


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
    alerts_data: list[BriefingAlert],
    user_id: str = "2d620133-08e5-49c1-ae8b-94e85adf29b1",
    authenticated: bool = Depends(verify_briefing_api_key)
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
            "alert_type": "above",
            "target_price": 24500,
            "description": "Breakout level",
            "notes": "Expected to reach 25000 if breakout confirmed"
        },
        ...
    ]
    """
    logger.info(f"Briefing API authenticated - creating {len(alerts_data)} alerts")

    try:
        created = []
        skipped = []

        for alert in alerts_data:
            try:
                alert_record = {
                    "user_id": user_id,
                    "symbol": alert.symbol,
                    "alert_type": alert.alert_type,
                    "target_price": alert.target_price,
                    "is_active": True,
                    "notify_telegram": True,
                    "repeat_mode": "one_shot",
                    "notes": f"{alert.description} — {alert.notes}" if alert.description else alert.notes,
                }
                db.client.table("watchlist_alerts").insert(alert_record).execute()
                created.append({
                    "symbol": alert.symbol,
                    "alert_type": alert.alert_type,
                    "target_price": alert.target_price
                })
                logger.info(f"Alert created from briefing: {alert.symbol} {alert.alert_type} {alert.target_price}")
            except Exception as e:
                skipped.append({"alert": alert.dict(), "reason": str(e)})

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
        raise HTTPException(status_code=500, detail="Failed to create alerts from briefing")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
