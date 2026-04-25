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
        logger.info("Telegram bot initialized")

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", cmd_start))
        self.app.add_handler(CommandHandler("watchlist", cmd_watchlist))
        self.app.add_handler(CommandHandler("add", cmd_add))
        self.app.add_handler(CommandHandler("remove", cmd_remove))
        self.app.add_handler(CommandHandler("positions", cmd_positions))
        self.app.add_handler(CommandHandler("status", cmd_status))

    async def start(self):
        logger.info("Starting Telegram bot polling")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def stop(self):
        logger.info("Stopping Telegram bot")
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def send_alert(self, symbol: str, alert_type: str, price: float, target: float):
        try:
            message = f"🚨 Alert: {symbol} {alert_type} {target}\n📍 Current: {price}"
            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=message
            )
            logger.info(f"Alert sent: {symbol} {alert_type}")
        except Exception as e:
            logger.error(f"Error sending alert: {e}")

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
