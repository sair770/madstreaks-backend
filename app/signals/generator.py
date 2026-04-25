from datetime import datetime
from app.config import logger


class SignalGenerator:
    def __init__(self, telegram_bot):
        self.telegram_bot = telegram_bot

    async def post_signal(self, symbol: str, direction: str, entry: float, target: float, stop_loss: float):
        signal_text = (
            f"<b>📊 Trade Signal</b>\n\n"
            f"<b>Symbol:</b> {symbol}\n"
            f"<b>Direction:</b> {direction}\n"
            f"<b>Entry:</b> {entry}\n"
            f"<b>Target:</b> {target}\n"
            f"<b>Stop Loss:</b> {stop_loss}\n"
            f"<b>R:R:</b> {self._calculate_rr(entry, target, stop_loss)}\n"
            f"<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await self.telegram_bot.send_signal(signal_text)
        logger.info(f"Signal posted: {symbol} {direction}")

    def _calculate_rr(self, entry: float, target: float, stop_loss: float) -> float:
        risk = abs(entry - stop_loss)
        reward = abs(target - entry)
        if risk == 0:
            return 0
        return round(reward / risk, 2)
