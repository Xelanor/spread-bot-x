import asyncio
import logging
import traceback
import importlib
import time

from app.celery import app
from celery.exceptions import SoftTimeLimitExceeded
from celery.schedules import crontab
from django.core.cache import cache

from spread.models import SpreadBot
from spread.spread_bot.spread_buy import SpreadBuy
from spread.spread_bot.spread_sell import SpreadSell
from spread.spread_bot.balance_cacher import SpreadBalanceCacherBot
from spread.spread_bot.depth_cacher import SpreadDepthCacherBot


@app.task
def run_spread_task(bot_id, side):
    bot = SpreadBot.objects.get(id=bot_id)
    bot.status = True
    bot.save()

    if side == "buy":
        run_spread_buy_bot.delay(bot_id)

    if side == "sell":
        run_spread_sell_bot.delay(bot_id)


@app.task(autoretry_for=(), max_retries=0, retry_backoff=False)
def run_spread_buy_bot(bot_id):
    bot = SpreadBuy(bot_id)
    bot.run()


@app.task(autoretry_for=(), max_retries=0, retry_backoff=False)
def run_spread_sell_bot(bot_id):
    bot = SpreadSell(bot_id)
    bot.run()


@app.task(autoretry_for=(), max_retries=0, retry_backoff=False)
def run_spread_depth_cacher_bot(bot_id):
    bot = SpreadDepthCacherBot(bot_id)
    bot.run()


@app.task(autoretry_for=(), max_retries=0, retry_backoff=False)
def run_spread_balance_cacher_bot():
    bot = SpreadBalanceCacherBot()
    bot.run()
