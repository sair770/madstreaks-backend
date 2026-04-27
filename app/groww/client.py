import pyotp
import time
from growwapi import GrowwAPI
from app.config import settings, logger
from app.groww.token_cache import GrowwTokenCache


class GrowwClient:
    def __init__(self):
        self.api = None
        self.authenticated = False
        self.token_cache = GrowwTokenCache()
        # Lazy authentication: only auth when feed starts, not at module load

    def _authenticate_with_retry(self, max_retries: int = 3):
        """Authenticate with exponential backoff on rate limit errors"""
        retry_delay = 1  # Start with 1 second

        for attempt in range(max_retries):
            try:
                # Try to get cached token first
                cached_token = self.token_cache.get_cached_token()
                if cached_token:
                    logger.info("Using cached Groww access token")
                    access_token = cached_token
                else:
                    # Get fresh access token using API key + secret
                    logger.info(f"Fetching new Groww access token (attempt {attempt + 1}/{max_retries})")
                    token_response = GrowwAPI.get_access_token(
                        api_key=settings.groww_api_key,
                        secret=settings.groww_api_secret
                    )

                    # token_response can be dict or string
                    if isinstance(token_response, dict):
                        access_token = token_response.get("access_token")
                    else:
                        access_token = token_response

                    if not access_token:
                        raise ValueError(f"No access token in response: {token_response}")

                    # Save to cache
                    self.token_cache.save_token(access_token)
                    logger.info("Got new access token from Groww (cached)")

                # Initialize API with access token
                self.api = GrowwAPI(access_token)
                self.authenticated = True
                logger.info("✅ Groww API authenticated")
                return

            except Exception as e:
                error_msg = str(e).lower()
                is_rate_limit = "429" in error_msg or "rate limit" in error_msg

                if is_rate_limit and attempt < max_retries - 1:
                    logger.warning(f"⚠️  Groww rate limit hit, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"⚠️  Groww authentication failed (non-blocking): {e}")
                    if is_rate_limit:
                        logger.info("Rate limit exceeded, clearing cache for next retry")
                        self.token_cache.clear_cache()
                    logger.info("Server will run without Groww integration")
                    return

    async def get_ltp(self, symbol: str) -> float | None:
        if not self.authenticated:
            return None
        try:
            data = self.api.get_quote(symbol)
            if isinstance(data, dict):
                return data.get("ltp")
            return None
        except Exception as e:
            logger.error(f"Error fetching LTP for {symbol}: {e}")
            return None

    async def place_order(self, symbol: str, qty: int, price: float, order_type: str = "BUY") -> dict | None:
        if not self.authenticated:
            logger.warning("Cannot place order: Groww not authenticated")
            return None
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
        if not self.authenticated:
            return []
        try:
            return self.api.get_positions()
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    async def cancel_order(self, order_id: str) -> bool:
        if not self.authenticated:
            logger.warning("Cannot cancel order: Groww not authenticated")
            return False
        try:
            self.api.cancel_order(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False


groww_client = GrowwClient()
