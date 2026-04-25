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
        self.is_running = True
        self.task = asyncio.create_task(self._run())

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
            instruments = [
                {"exchange": "NSE", "segment": "CASH", "exchange_token": symbol}
                for symbol in symbols
            ]

            self.feed.subscribe_ltp(
                instruments,
                on_data_received=self._on_price_tick
            )

            # This is blocking, runs in thread
            self.feed.consume()

        except Exception as e:
            logger.error(f"Error in Groww feed thread: {e}")
            self.is_running = False

    def _on_price_tick(self, meta):
        try:
            if not self.is_running or not self.feed:
                return

            prices = self.feed.get_ltp()
            logger.debug(f"Price tick received: {prices}")

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
