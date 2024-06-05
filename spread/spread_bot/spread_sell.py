import os
import logging
import traceback
from time import sleep
import time

from django.core.cache import cache

from exchanges.api_classes import api_classes
from spread.models import (
    SpreadBot,
    Exchange,
    ExchangeApi,
    SpreadBotTx,
)
from .utils import SpreadUtilityFunctions


logger = logging.getLogger(__name__)


class SpreadSell:
    """Base class for Spread Sell Bot"""

    def __init__(self, bot_id):
        self.bot_id = bot_id
        self.bot = SpreadBot.objects.get(id=self.bot_id)
        self.exchange = self.bot.exchange.name

        self.set_bot_settings()

        self.api = self.setup_api()
        self.setup_logger()
        self.util_functions = SpreadUtilityFunctions(
            self.ticker, self.price_precision, self.quantity_precision
        )

        logger.debug(f"API: {self.api}")
        logger.info(f"Price Precision: {self.price_precision}")
        logger.info(f"Qty Precision: {self.quantity_precision}")

        self.order_id = None

    def setup_api(self):
        """Setup APIs"""
        api_obj = ExchangeApi.objects.get(exchange=self.bot.exchange)
        api = api_classes[api_obj.exchange.name](
            self.bot.ticker,
            api_obj.public_key,
            api_obj.private_key,
            api_obj.group,
            api_obj.kyc,
        )
        price_precision, quantity_precision = api.get_product_details()
        self.price_precision = price_precision
        self.quantity_precision = quantity_precision
        return api

    def setup_logger(self):
        filepath = f"logs/SpreadTrader/{self.exchange}"
        if not os.path.exists(filepath):
            os.makedirs(filepath)

        logFile = f"{filepath}/{self.tick}_SELL.log"
        f_handler = logging.handlers.RotatingFileHandler(
            logFile, maxBytes=5 * 1024 * 1024, backupCount=10
        )
        f_format = logging.Formatter(
            "%(asctime)s :: %(levelname)s :: %(lineno)d :: %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S",
        )
        f_handler.setFormatter(f_format)
        logger.addHandler(f_handler)

    def check_bot_status(self):
        """Check bot status"""

        self.bot = SpreadBot.objects.get(id=self.bot_id)
        return self.bot.sell_status

    def run(self):
        """Main starting point of Spread Sell Bot"""
        logger.info("Starting")
        sleep(5)
        while True:
            try:
                bot_status = self.check_bot_status()
                if bot_status == False:
                    self.check_order_status()
                    self.cancel_order()
                    self.apis[self.exchange].cancel_open_orders()
                    logger.warning(f"Bot stopped, closing job")
                    return False

                self.set_bot_settings()
                sleep(0.5)

            except Exception as ex:
                logger.critical(traceback.format_exc())
                sleep(5)
                pass
