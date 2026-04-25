from app.config import logger
from app.groww.client import groww_client


async def place_order(symbol: str, qty: int, price: float, order_type: str = "BUY") -> dict | None:
    response = await groww_client.place_order(symbol, qty, price, order_type)
    return response


async def cancel_order(order_id: str) -> bool:
    return await groww_client.cancel_order(order_id)


async def get_positions() -> list:
    return await groww_client.get_positions()


async def get_open_orders() -> list:
    try:
        orders = groww_client.api.get_orders()
        return [o for o in orders if o.get("status") == "OPEN"]
    except Exception as e:
        logger.error(f"Error fetching open orders: {e}")
        return []
