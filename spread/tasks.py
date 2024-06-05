import asyncio
import logging
import traceback
import importlib
import time

from app.celery import app
from celery.exceptions import SoftTimeLimitExceeded
from celery.schedules import crontab
from django.core.cache import cache

from spread.spread_bot.balance_cacher import SpreadBalanceCacherBot


@app.task(autoretry_for=(), max_retries=0, retry_backoff=False)
def run_spread_balance_cacher_bot():
    bot = SpreadBalanceCacherBot()
    bot.run()
