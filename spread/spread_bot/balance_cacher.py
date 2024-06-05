import asyncio

from channels.db import database_sync_to_async
from django.core.cache import cache

from exchanges.api_classes import ws_classes
from spread.models import ExchangeApi

from app.celery import app


@app.task(autoretry_for=(), max_retries=0, retry_backoff=False)
def run_spread_exchange_balance_cacher_bot(exchange, api_object):
    def balance(exchange, kyc, balance):
        cache.set(f"{exchange}_{kyc}_balances", balance, 60 * 60)

    WS_class = ws_classes[exchange](
        "",
        api_object["public_key"],
        api_object["private_key"],
        api_object["group"],
        api_object["kyc"],
    )
    asyncio.run(WS_class.main(balance=balance))


class SpreadBalanceCacherBot:
    def get_exchange_apis(self):
        api_objects = list(
            ExchangeApi.objects.filter().values(
                "exchange__name",
                "public_key",
                "private_key",
                "group",
                "kyc",
            )
        )
        return api_objects

    def start_ws(self):
        api_objects = self.get_exchange_apis()
        for api_object in api_objects:
            run_spread_exchange_balance_cacher_bot.delay(
                api_object["exchange__name"], api_object
            )

    def run(self):
        self.start_ws()
