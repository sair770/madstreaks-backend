from datetime import datetime
from app.config import logger
from app.database import db


class AlertManager:
    def __init__(self, notifier):
        self.notifier = notifier

    async def get_active_symbols(self) -> list:
        alerts = await db.get_active_alerts()
        symbols = list(set(a.get("symbol") for a in alerts if a.get("symbol")))
        logger.info(f"Active symbols: {symbols}")
        return symbols

    async def check(self, prices: dict):
        alerts = await db.get_active_alerts()

        for alert in alerts:
            symbol = alert.get("symbol")
            alert_id = alert.get("id")

            price = self._extract_price(prices, symbol)
            if price is None:
                continue

            current_ts = datetime.utcnow().isoformat() + "Z"
            await db.update_alert_price(alert_id, price, current_ts)

            if self._is_triggered(alert, price) and not alert.get("alert_triggered"):
                await db.mark_alert_triggered(alert_id, current_ts)
                await self.notifier.send(alert, price)

    def _extract_price(self, prices: dict, symbol: str) -> float | None:
        try:
            if not prices or not isinstance(prices, dict):
                return None

            ltp_data = prices.get("ltp", {})
            nse_data = ltp_data.get("NSE", {})
            cash_data = nse_data.get("CASH", {})

            for token, data in cash_data.items():
                if isinstance(data, dict) and "ltp" in data:
                    return float(data["ltp"])

            return None
        except Exception as e:
            logger.error(f"Error extracting price for {symbol}: {e}")
            return None

    def _is_triggered(self, alert: dict, price: float) -> bool:
        alert_type = alert.get("alert_type")
        if alert_type == "above":
            target = alert.get("target_price")
            return target is not None and price >= target

        elif alert_type == "below":
            target = alert.get("target_price")
            return target is not None and price <= target

        elif alert_type == "pct_change":
            base = alert.get("base_price")
            pct = alert.get("pct_change")
            if base is not None and pct is not None:
                change = abs((price - base) / base * 100)
                return change >= pct

        return False
