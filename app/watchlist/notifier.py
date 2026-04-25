from app.config import logger


class Notifier:
    def __init__(self, telegram_bot):
        self.telegram_bot = telegram_bot

    async def send(self, alert: dict, current_price: float):
        symbol = alert.get("symbol")
        alert_type = alert.get("alert_type")
        notify_telegram = alert.get("notify_telegram", False)
        notify_groww = alert.get("notify_groww", False)

        if alert_type == "pct_change":
            target = alert.get("pct_change")
            base = alert.get("base_price")
            message = f"🚨 {symbol}: {target}% change from {base} → {current_price}"
        else:
            target = alert.get("target_price")
            message = f"🚨 {symbol} went {alert_type} {target} → {current_price}"

        if notify_telegram:
            await self.telegram_bot.send_alert(symbol, alert_type, current_price, alert.get("target_price"))
            logger.info(f"Telegram alert sent: {symbol}")

        if notify_groww:
            logger.info(f"Groww notification queued: {symbol} (Groww GTT phase 2 - TBD)")

        logger.info(f"Alert triggered: {message}")
