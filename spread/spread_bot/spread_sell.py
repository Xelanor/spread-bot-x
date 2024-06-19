import os
import logging
import traceback
from time import sleep
import time

from django.core.cache import cache
from django.utils.timezone import now

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

        self.sell_order_id = None

        self.previous_deal_timer = time.time()
        self.previous_deals = {}

        self.unrecorded_amount = None

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

    def set_bot_settings(self):
        """Set bot settings"""
        self.bot = SpreadBot.objects.get(id=self.bot_id)

        self.ticker = self.bot.ticker
        self.tick = self.ticker.split("/")[0]
        self.point = self.bot.point
        self.budget = self.bot.budget
        self.spread_rate = self.bot.spread_rate
        self.average_price = self.bot.average_price
        self.sellable_quantity = self.bot.sellable_quantity
        self.max_size = self.bot.max_size
        self.profit_rate = self.bot.profit_rate
        self.take_profit_rate = self.bot.take_profit_rate
        self.average_correction_minutes = self.bot.average_correction_minutes
        self.average_correction_rate = self.bot.average_correction_rate

    def get_depth(self):
        """Get depth from cache"""
        depth = cache.get(f"{self.ticker}_{self.exchange}_depth")
        return depth

    def get_balances(self):
        """Get balances from cache"""
        key = f"{self.exchange}_Berke_balances"
        balance = cache.get(key)
        if not self.tick in balance:
            balance[self.tick] = {
                "available": 0,
                "frozen": 0,
                "total": 0,
            }

        return balance

    def check_deal_condition(self, new_deal):
        if new_deal["quantity"] < self.deal["quantity"] * 0.95:
            logger.info(f"Quantity changed, cancelling order")
            self.cancel_order()
            self.deal = None
            return True

        if new_deal["quantity"] > self.deal["quantity"] * 1.20:
            logger.info(f"Quantity changed, cancelling order")
            self.cancel_order()
            self.deal = None
            return True

        depth = self.get_depth()
        lowest_ask = float(depth["asks"][0][0])
        second_lowest_ask = float(depth["asks"][1][0])

        if lowest_ask > self.deal["sell_price"]:
            logger.error(
                f"Order book may be outdated, Exchange: {self.exchange} Ticker: {self.ticker}"
            )
            return False

        if not lowest_ask == self.deal["sell_price"]:  # Gerideyiz
            logger.info(f"Sell order is not the best, canceling order...")
            self.cancel_order()
            self.deal = None
            return True

        behind_price = self.util_functions.determine_order_price(
            side="SELL", lowest_ask=second_lowest_ask
        )
        if not lowest_ask == behind_price:  # En öndeyiz ama arkadakine uzağız
            logger.info(f"Sell order is best but not close to behind, canceling order")
            self.cancel_order()
            self.deal = None
            return True

    def add_to_previous_deals(self):
        if not self.deal:
            return

        self.previous_deals[self.sell_order_id] = self.deal

    def check_previous_deals(self):
        elapsed_time = time.time() - self.previous_deal_timer
        if elapsed_time < 5:
            return

        for order_id in self.previous_deals.copy():
            filled_price, filled_quantity, res = self.api.get_order_status(order_id)

            if filled_quantity == 0:
                del self.previous_deals[order_id]
                self.previous_deal_timer = time.time()  # Timer Updated
                continue

            logger.info(
                f"Checked - Order is actually filled qty: {filled_quantity}/{self.previous_deals[order_id]['quantity']}"
            )
            self.previous_deals[order_id]["sell_filled_price"] = filled_price
            self.previous_deals[order_id]["sell_filled_qty"] = filled_quantity

            self.update_average_price_and_sellable_qty(filled_price, filled_quantity)
            self.record_transaction(self.previous_deals[order_id])

            del self.previous_deals[order_id]
            self.previous_deal_timer = time.time()  # Timer Updated
            sleep(0.5)

    def cancel_order(self, record=True):
        if self.sell_order_id:
            if record:
                self.add_to_previous_deals()

            self.api.cancel_order(self.sell_order_id)
            logger.info(f"Cancelled Order")
            self.sell_order_id = None

    def record_transaction(self, deal):
        transaction = {
            "bot": self.bot,
            "buy_price": self.average_price,
            "sell_price": deal["sell_filled_price"],
            "quantity": deal["sell_filled_qty"],
            "side": "sell",
            "condition": "M",
        }

        fee_rates = {
            "Mexc": 0.001,
            "Bitmart": 0.0025,
            "Kucoin": 0.001,
            "BingX": 0.001,
            "Bybit": 0.001,
            "Bitget": 0.001,
            "XT": 0.002,
        }

        fee = (
            deal["sell_filled_price"]
            * deal["sell_filled_qty"]
            * fee_rates[self.exchange]
        )
        transaction["fee"] = fee

        profit = (deal["sell_filled_price"] - self.average_price) * deal[
            "sell_filled_qty"
        ]
        transaction["profit"] = profit - fee

        SpreadBotTx.objects.create(**transaction)

    def check_deal(self):
        depth = self.get_depth()
        balances = self.get_balances()

        if not depth:
            logger.error(f"Unable to reach cached depth")
            return False

        if not balances:
            logger.error(f"Unable to reach cached balances")
            return False

        sell_deal_price = float(depth["asks"][0][0])
        if not self.sell_order_id:  # Aktif order yoksa
            sell_deal_price = self.util_functions.determine_order_price(
                side="SELL", lowest_ask=sell_deal_price
            )

        total_usdt = balances["USDT"]["total"]
        available_usdt = balances["USDT"]["available"]
        logger.debug(f"Total USDT: {total_usdt} - Available USDT: {available_usdt}")

        available_tokens = self.average_price * self.sellable_quantity

        trade_size = available_tokens

        if trade_size < 6:
            logger.warning(f"Trade size is too low: {trade_size}")
            return False

        profit_rate = self.util_functions.calculate_profit_rate(
            self.average_price, sell_deal_price
        )
        is_profitable = self.util_functions.is_trade_profitable(
            profit_rate, self.profit_rate
        )

        if not is_profitable:
            logger.info(
                f"Profit rate is not enough: {profit_rate}, trying to enter at ask price"
            )

            sell_deal_price = float(depth["asks"][0][0])
            profit_rate = self.util_functions.calculate_profit_rate(
                self.average_price, sell_deal_price
            )
            is_profitable = self.util_functions.is_trade_profitable(
                profit_rate, self.profit_rate
            )
            if is_profitable:
                logger.info(f"Will be entered at ask price: {sell_deal_price}")

        if not is_profitable:
            logger.info(f"Profit rate is not enough: {profit_rate}")
            return False

        quantity = trade_size / sell_deal_price

        deal = {
            "buy_price": self.average_price,
            "sell_price": sell_deal_price,
            "quantity": quantity,
            "profit_rate": profit_rate,
        }
        logger.debug(f"Deal: {deal}")
        return deal

    def unrecorded_buy_correction(self):
        """Sometimes buy bot cannot record some transactions this function corrects it"""
        key = f"last_buy_correction_time_{self.bot_id}"
        last_correction = cache.get(key)
        if last_correction:
            return True

        balances = self.get_balances()
        if self.tick not in balances:
            total_balance = 0
        else:
            total_balance = balances[self.tick]["total"]

        logger.debug(
            f"Total balance: {total_balance} - Sellable Quantity: {self.sellable_quantity}"
        )

        if self.sellable_quantity == total_balance:
            logger.debug(f"Bot has no unrecorded buy transactions")
            return True

        difference = total_balance - self.sellable_quantity
        difference_value = difference * self.average_price

        if self.unrecorded_amount != difference:
            self.unrecorded_amount = difference
            cache.set(key, True, 15)
            return True

        if difference < 0:
            bot = SpreadBot.objects.get(id=self.bot_id)
            bot.sellable_quantity = total_balance
            if total_balance == 0:
                bot.average_price = 0
            bot.save()

            self.sellable_quantity = total_balance
            logger.warning(f"Bot has unrecorded sell transactions, correcting...")
            return True

        if difference_value < 0.5:
            cache.set(key, True, 15)
            return True

        bot = SpreadBot.objects.get(id=self.bot_id)

        logger.warning(f"Bot has unrecorded buy transactions, correcting...")
        bot.sellable_quantity = total_balance
        bot.save()

        cache.set(key, True, 15)
        return True

    def record_last_order_placed_time(self):
        """Every 3 minutes record order placed time"""
        key = f"last_sell_order_placed_time_{self.bot_id}"
        last_order_placed = cache.get(key)

        if last_order_placed:
            return True

        bot = SpreadBot.objects.get(id=self.bot_id)
        bot.last_sell_order_date = now()
        bot.save()

        cache.set(key, True, 180)
        return True

    def execute_deal(self, deal):
        order_price = deal["sell_price"]
        quantity = deal["quantity"]

        order_price_formatted = self.util_functions.format_order_price(order_price)
        order_qty = self.util_functions.determine_qty_down(quantity)
        order_id, res = self.api.create_limit_order(
            "sell", order_price_formatted, order_qty
        )
        if not order_id:
            logger.error(f"Order failed: {res}")
            return "FAILED"

        self.sell_order_id = order_id
        deal["sell_order_price"] = order_price
        deal["sell_order_qty"] = order_qty

        self.deal = deal
        logger.info(f"Sell Order placed at {order_price} with quantity {order_qty}")
        self.record_last_order_placed_time()
        return True

    def update_average_price_and_sellable_qty(self, price, quantity):
        bot = SpreadBot.objects.get(id=self.bot_id)
        sellable_qty = bot.sellable_quantity

        new_sellable_qty = self.util_functions.determine_partial_qty(
            sellable_qty, quantity
        )
        bot.sellable_quantity = new_sellable_qty

        if new_sellable_qty == 0:
            bot.average_price = 0

        bot.save()
        return True

    def check_order_status(self):
        if not self.sell_order_id:
            return "NO_CURRENT_ORDER"

        filled_price, filled_quantity, res = self.api.get_order_status(
            self.sell_order_id
        )

        if filled_quantity == 0:
            return "NO_FILL"

        self.cancel_order(record=False)
        logger.info(f"Order is filled qty: {filled_quantity}/{self.deal['quantity']}")

        self.deal["sell_filled_price"] = filled_price
        self.deal["sell_filled_qty"] = filled_quantity

        self.update_average_price_and_sellable_qty(filled_price, filled_quantity)

        self.record_transaction(self.deal)
        self.deal = None
        return True

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
                    # self.api.cancel_open_orders()
                    logger.warning(f"Bot stopped, closing job")
                    return False

                self.set_bot_settings()
                self.check_previous_deals()
                self.unrecorded_buy_correction()

                deal = self.check_deal()
                if not deal and self.sell_order_id:  # Deal artık yok order varsa iptal
                    self.check_order_status()
                    self.cancel_order()

                if deal and not self.sell_order_id:  # Deal var order yok alım gir
                    self.execute_deal(deal)

                if deal and self.sell_order_id:  # Deal var order var durumu kontrol et
                    self.check_order_status()

                if (
                    deal and self.sell_order_id
                ):  # Deal var, order gerçekleşmemiş ama deal geçerli mi?
                    self.check_deal_condition(deal)

                sleep(0.5)

            except Exception as ex:
                logger.critical(traceback.format_exc())
                sleep(5)
                pass
