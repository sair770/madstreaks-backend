from telegram import Bot
from app.config import settings, logger


class TelegramBot:
    """Send-only Telegram bot — no polling, just message delivery to groups/channels"""
    def __init__(self):
        self.token = settings.telegram_bot_token
        logger.info("Telegram bot initialized (send-only mode)")

    async def start(self):
        """No-op: no polling needed"""
        logger.info("✅ Telegram ready (message sending enabled)")

    async def stop(self):
        """No-op: no resources to clean up"""
        logger.info("Telegram stopped")

    async def send_alert(self, symbol: str, alert_type: str, price: float, target: float):
        """Send triggered alert to alerts group (works independent of polling)"""
        try:
            message = f"🚨 Alert: {symbol} {alert_type} {target}\n📍 Current: {price}"
            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=settings.telegram_alerts_group_id,
                text=message
            )
            logger.info(f"✅ Alert sent to alerts group: {symbol} {alert_type}")
        except Exception as e:
            logger.error(f"❌ Error sending alert: {e}")

    async def send_to_personal_chat(self, message: str):
        """Send message to personal chat"""
        try:
            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=message
            )
            logger.info("Message sent to personal chat")
        except Exception as e:
            logger.error(f"Error sending to personal chat: {e}")

    async def send_trade_notification(self, symbol: str, entry_price: float, trade_type: str, target: float = None, stop_loss: float = None):
        """Send new trade notification to trades ops group (works independent of polling)"""
        try:
            message = f"📈 New Trade: {symbol}\n"
            message += f"Type: {trade_type.upper()}\n"
            message += f"Entry: ₹{entry_price}\n"
            if target:
                message += f"Target: ₹{target}\n"
            if stop_loss:
                message += f"SL: ₹{stop_loss}\n"
            message += f"Time: {__import__('datetime').datetime.now().strftime('%H:%M IST')}"

            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=settings.telegram_trades_group_id,
                text=message
            )
            logger.info(f"✅ Trade notification sent: {symbol}")
        except Exception as e:
            logger.error(f"❌ Error sending trade notification: {e}")

    async def send_alert_notification(self, symbol: str, alert_type: str, target_price: float):
        """Send new watchlist alert notification to trades ops group (works independent of polling)"""
        try:
            message = f"⏰ New Watchlist Alert\n"
            message += f"Symbol: {symbol}\n"
            message += f"Type: {alert_type.upper()}\n"
            message += f"Target: ₹{target_price}\n"
            message += f"Time: {__import__('datetime').datetime.now().strftime('%H:%M IST')}"

            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=settings.telegram_trades_group_id,
                text=message
            )
            logger.info(f"✅ Alert notification sent: {symbol}")
        except Exception as e:
            logger.error(f"❌ Error sending alert notification: {e}")

    async def send_signal(self, signal_text: str):
        try:
            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=settings.telegram_channel_id,
                text=signal_text,
                parse_mode="HTML"
            )
            logger.info("Signal posted to channel")
        except Exception as e:
            logger.error(f"Error posting signal: {e}")


telegram_bot = TelegramBot()
