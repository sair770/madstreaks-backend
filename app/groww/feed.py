import asyncio
from growwapi import GrowwFeed
from app.config import settings, logger
from app.groww.client import groww_client


class FeedManager:
    def __init__(self, alert_manager):
        self.groww = groww_client
        self.feed = None
        self.alert_manager = alert_manager
        self.is_running = False
        self.task = None

    async def start(self):
        logger.info("Starting Groww feed manager")
        self.is_running = True
        self.task = asyncio.create_task(self._run())

    async def _run(self):
        try:
            if self.feed is None:
                self.feed = GrowwFeed(self.groww.api)
                logger.info("GrowwFeed initialized")

            symbols = await self.alert_manager.get_active_symbols()
            if not symbols:
                logger.warning("No active symbols to monitor")
                return

            logger.info(f"Subscribing to {len(symbols)} symbols: {symbols}")

            instruments = [
                {"exchange": "NSE", "segment": "CASH", "exchange_token": symbol}
                for symbol in symbols
            ]

            self.feed.subscribe_ltp(
                instruments,
                on_data_received=self._on_price_tick
            )

            await asyncio.to_thread(self.feed.consume)

        except Exception as e:
            logger.error(f"Error in feed loop: {e}")
            self.is_running = False

    def _on_price_tick(self, meta):
        try:
            if self.is_running:
                prices = self.feed.get_ltp()
                loop = asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(
                    self.alert_manager.check(prices),
                    loop
                )
        except Exception as e:
            logger.error(f"Error processing price tick: {e}")

    async def stop(self):
        logger.info("Stopping Groww feed manager")
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def refresh_symbols(self):
        logger.info("Refreshing monitored symbols")
        await self.stop()
        await asyncio.sleep(1)
        await self.start()
