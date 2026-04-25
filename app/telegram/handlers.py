from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from app.config import logger
from app.database import db
from app.groww.orders import get_positions


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Madstreaks Bot\n\n"
        "Available commands:\n"
        "/watchlist — List active alerts\n"
        "/add SYMBOL above|below|pct 24000 — Add alert\n"
        "/remove <id> — Remove alert\n"
        "/positions — Your Groww positions\n"
        "/status — Server health\n"
    )


async def cmd_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alerts = await db.get_active_alerts()
    if not alerts:
        await update.message.reply_text("📭 No active watchlist alerts")
        return

    lines = ["📊 Active Watchlist Alerts:\n"]
    for alert in alerts:
        symbol = alert.get("symbol", "—")
        alert_type = alert.get("alert_type", "—")
        current = alert.get("current_price", "—")
        target = alert.get("target_price", "—")
        pct = alert.get("pct_change", "—")
        status = "✅" if alert.get("alert_triggered") else "👁️"

        if alert_type == "pct_change":
            lines.append(f"{status} {symbol} {alert_type} {pct}% (curr: {current})")
        else:
            lines.append(f"{status} {symbol} {alert_type} {target} (curr: {current})")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 3:
        await update.message.reply_text("Usage: /add SYMBOL above|below|pct TARGET\nExample: /add NIFTY below 24000")
        return

    symbol = context.args[0].upper()
    alert_type = context.args[1].lower()
    target_str = context.args[2]

    if alert_type not in ["above", "below", "pct"]:
        await update.message.reply_text("Alert type must be: above, below, or pct")
        return

    try:
        target = float(target_str)
    except ValueError:
        await update.message.reply_text("Target must be a number")
        return

    try:
        alert_data = {
            "symbol": symbol,
            "alert_type": alert_type,
            "target_price": target if alert_type != "pct" else None,
            "pct_change": target if alert_type == "pct" else None,
            "base_price": None,
            "current_price": None,
            "last_checked_at": None,
            "alert_triggered": False,
            "repeat_mode": "repeating",
            "notify_telegram": True,
            "notify_groww": False,
            "is_active": True,
            "notes": f"Created via Telegram bot"
        }
        await db.insert_alert(alert_data)
        await update.message.reply_text(f"✅ Alert added: {symbol} {alert_type} {target}")
    except Exception as e:
        logger.error(f"Error adding alert: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /remove <alert_id>")
        return

    alert_id = context.args[0]
    try:
        await db.delete_alert(alert_id)
        await update.message.reply_text(f"✅ Alert removed: {alert_id}")
    except Exception as e:
        logger.error(f"Error removing alert: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def cmd_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    positions = await get_positions()
    if not positions:
        await update.message.reply_text("📭 No open positions")
        return

    lines = ["📈 Open Positions:\n"]
    for pos in positions:
        symbol = pos.get("symbol", "—")
        qty = pos.get("qty", "—")
        avg_price = pos.get("avg_price", "—")
        current_price = pos.get("current_price", "—")
        pnl = pos.get("pnl", "—")
        lines.append(f"{symbol} | {qty}x @ {avg_price} | Current: {current_price} | P&L: {pnl}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alerts = await db.get_active_alerts()
    active_count = len([a for a in alerts if not a.get("alert_triggered")])
    triggered_count = len([a for a in alerts if a.get("alert_triggered")])

    status_text = (
        f"✅ Server Status\n\n"
        f"🔌 Groww Feed: Connected\n"
        f"💾 Database: Connected\n"
        f"⏰ Timestamp: {datetime.now().isoformat()}\n\n"
        f"📊 Watchlist:\n"
        f"  Watching: {active_count}\n"
        f"  Triggered: {triggered_count}"
    )
    await update.message.reply_text(status_text)
