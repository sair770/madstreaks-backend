from telegram import Bot
from telegram.ext import Application, CommandHandler
from app.config import settings, logger
from app.telegram.handlers import (
    cmd_start, cmd_watchlist, cmd_add, cmd_remove,
    cmd_positions, cmd_status
)


class TelegramBot:
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.app = Application.builder().token(self.token).build()
        self._setup_handlers()
        self.task = None
        self.polling_active = False
        logger.info("Telegram bot initialized")

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", cmd_start))
        self.app.add_handler(CommandHandler("watchlist", cmd_watchlist))
        self.app.add_handler(CommandHandler("add", cmd_add))
        self.app.add_handler(CommandHandler("remove", cmd_remove))
        self.app.add_handler(CommandHandler("positions", cmd_positions))
        self.app.add_handler(CommandHandler("status", cmd_status))

    async def start(self):
        if self.polling_active:
            logger.warning("Telegram bot polling already active, skipping restart")
            return

        logger.info("Starting Telegram bot polling")
        self.polling_active = True
        try:
            await self.app.initialize()
            await self.app.start()
            # allow_recovery=True: continue polling on 409 Conflict errors
            await self.app.updater.start_polling(allowed_updates=None, drop_pending_updates=True)
        except Exception as e:
            if "409" in str(e) or "Conflict" in str(e):
                logger.error(f"⚠️  Telegram 409 Conflict: bot already polling elsewhere. Disabling polling.")
                self.polling_active = False
                # Continue running without polling — message sending still works
            else:
                logger.error(f"Telegram bot error: {e}")
                self.polling_active = False

    async def stop(self):
        logger.info("Stopping Telegram bot")
        self.polling_active = False
        try:
            await self.app.updater.stop()
        except Exception as e:
            logger.warning(f"Updater stop error: {e}")
        try:
            await self.app.stop()
        except Exception as e:
            logger.warning(f"App stop error: {e}")
        try:
            await self.app.shutdown()
        except Exception as e:
            logger.warning(f"App shutdown error: {e}")

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
