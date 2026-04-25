from growwapi import GrowwAPI
from app.config import settings, logger


class GrowwClient:
    def __init__(self):
        self.api = GrowwAPI(settings.groww_api_key)
        logger.info("Groww API client initialized")

    async def get_ltp(self, symbol: str) -> float | None:
        try:
            data = self.api.get_quote(symbol)
            return data.get("ltp")
        except Exception as e:
            logger.error(f"Error fetching LTP for {symbol}: {e}")
            return None

    async def place_order(self, symbol: str, qty: int, price: float, order_type: str = "BUY") -> dict | None:
        try:
            response = self.api.place_order(
                symbol=symbol,
                qty=qty,
                price=price,
                order_type=order_type
            )
            logger.info(f"Order placed: {symbol} {qty} @ {price}")
            return response
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    async def get_positions(self) -> list:
        try:
            return self.api.get_positions()
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    async def cancel_order(self, order_id: str) -> bool:
        try:
            self.api.cancel_order(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False


groww_client = GrowwClient()
