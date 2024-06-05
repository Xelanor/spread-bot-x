import asyncio

from channels.db import database_sync_to_async
from django.core.cache import cache

from exchanges.api_classes import ws_classes
from spread.models import SpreadBot, ExchangeApi


class SpreadDepthCacherBot:
    def __init__(self, bot_id):
        self.bot_id = bot_id

    def depth(self, exchange, asks, bids):
        depth = {"asks": asks, "bids": bids}
        cache.set(f"{self.ticker}_{exchange}_depth", depth, 5 * 60)

    @database_sync_to_async
    def get_trader_model(self):
        return SpreadBot.objects.get(id=self.bot_id)

    @database_sync_to_async
    def get_exchange_apis(self, exchange):
        api_objects = list(ExchangeApi.objects.filter(exchange=exchange).values())
        return api_objects

    async def start_ws(self):
        tasks = []
        self.bot = await self.get_trader_model()
        self.ticker = self.bot.ticker
        self.tick = self.ticker.split("/")[0]
        exchange = self.bot.exchange

        api_objects = await self.get_exchange_apis(exchange)
        for api_object in api_objects:
            tasks.append(
                ws_classes[exchange.name](
                    self.ticker,
                    api_object["public_key"],
                    api_object["private_key"],
                    api_object["group"],
                    api_object["kyc"],
                ).main(depth=self.depth)
            )

        await asyncio.gather(*tasks)

    def run(self):
        asyncio.run(self.start_ws())
