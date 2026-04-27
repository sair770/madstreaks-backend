import asyncio
import threading
from growwapi import GrowwFeed
from app.config import logger
from app.groww.client import groww_client


class FeedManager:
    def __init__(self, alert_manager):
        self.groww = groww_client
        self.alert_manager = alert_manager
        self.is_running = False
        self.feed = None
        self.feed_thread = None
        self.task = None

    async def start(self):
        logger.info("Starting Groww live feed")
        # Lazy authenticate if not already done
        if not self.groww.authenticated:
            logger.info("Attempting Groww authentication for feed startup...")
            self.groww._authenticate_with_retry()

        if not self.groww.authenticated:
            logger.warning("⚠️  Groww not authenticated — scheduling retry in 30s...")
            # Schedule a retry in 30 seconds
            asyncio.create_task(self._delayed_start(30))
            return

        self.is_running = True
        self.task = asyncio.create_task(self._run())

    async def _delayed_start(self, delay: int):
        """Retry feed start after delay (for rate limit recovery)"""
        logger.warning(f"Feed start scheduled to retry in {delay}s (waiting for Groww rate limit reset)")
        await asyncio.sleep(delay)
        logger.info(f"🔄 Retrying Groww feed after {delay}s delay...")
        await self.start()

    async def _run(self):
        try:
            # Run Groww feed in thread pool to avoid event loop conflict
            await asyncio.to_thread(self._start_feed_in_thread)
        except Exception as e:
            logger.error(f"Error in feed manager: {e}")
            self.is_running = False

    def _start_feed_in_thread(self):
        try:
            symbols = asyncio.run(self.alert_manager.get_active_symbols())
            if not symbols:
                logger.warning("No active symbols to monitor")
                return

            logger.info(f"Subscribing to Groww feed for {len(symbols)} symbols: {symbols}")

            self.feed = GrowwFeed(self.groww.api)

            # Convert symbol names to exchange tokens
            instruments = []
            for symbol in symbols:
                try:
                    instrument = self.groww.api.get_instrument_by_exchange_and_trading_symbol(
                        exchange="NSE",
                        trading_symbol=symbol
                    )
                    if instrument:
                        exchange_token = instrument.get("exchange_token") or instrument.get("token")
                        instruments.append({
                            "exchange": "NSE",
                            "segment": "CASH",
                            "exchange_token": str(exchange_token)
                        })
                        logger.info(f"Found token for {symbol}: {exchange_token}")
                    else:
                        logger.warning(f"Could not find exchange token for {symbol}")
                except Exception as e:
                    logger.warning(f"Error getting token for {symbol}: {e}")

            if not instruments:
                logger.error("No valid instruments to subscribe to")
                return

            logger.info(f"Calling feed.subscribe_ltp() with {len(instruments)} instruments")
            result = self.feed.subscribe_ltp(
                instruments,
                on_data_received=self._on_price_tick
            )
            logger.info(f"subscribe_ltp result: {result}")
            logger.info(f"Subscribed to {len(instruments)} instruments: {instruments}")
            logger.info("Starting feed.consume() - waiting for price ticks...")
            # This is blocking, runs in thread
            self.feed.consume()
            logger.warning("feed.consume() exited")

        except Exception as e:
            logger.error(f"Error in Groww feed thread: {e}")
            self.is_running = False

    def _on_price_tick(self, meta):
        try:
            if not self.is_running or not self.feed:
                return

            prices = self.feed.get_ltp()
            if prices:
                logger.info(f"💰 Price tick received: {prices}")
            else:
                logger.warning("Price tick but no prices returned")

            # Schedule check in main event loop
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                self.alert_manager.check(prices),
                loop
            )
        except Exception as e:
            logger.error(f"Error in price tick: {e}")

    async def stop(self):
        logger.info("Stopping Groww feed")
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def refresh_symbols(self):
        logger.info("Refreshing Groww feed symbols")
        await self.stop()
        await asyncio.sleep(1)
        await self.start()
