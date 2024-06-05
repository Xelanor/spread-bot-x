import math
from decimal import Decimal


class SpreadUtilityFunctions:
    def __init__(self, ticker, price_precision, quantity_precision):
        self.ticker = ticker
        self.price_precision = price_precision
        self.quantity_precision = quantity_precision

    def determine_order_price(self, side, lowest_ask=None, highest_bid=None):
        decimal_count = Decimal(str(self.price_precision)).as_tuple().exponent * -1
        if side == "BUY":
            return round(highest_bid + self.price_precision, decimal_count)
        if side == "SELL":
            return round(lowest_ask - self.price_precision, decimal_count)

    def format_order_price(self, order_price):
        decimal_count = Decimal(str(self.price_precision)).as_tuple().exponent * -1
        order_price_formatted = format(order_price, f".{decimal_count}f")
        return order_price_formatted

    def determine_qty_down(self, qty):
        decimal_count = Decimal(str(self.quantity_precision)).as_tuple().exponent * -1
        factor = 10**decimal_count
        remaining_qty = math.floor(qty * factor) / factor

        return remaining_qty

    def determine_price_down(self, price):
        decimal_count = Decimal(str(self.price_precision)).as_tuple().exponent * -1
        factor = 10**decimal_count
        order_price = math.floor(price * factor) / factor

        return order_price

    def determine_price_up(self, price):
        decimal_count = Decimal(str(self.price_precision)).as_tuple().exponent * -1
        factor = 10**decimal_count
        order_price = math.ceil(price * factor) / factor

        return order_price

    def calculate_profit_rate(self, buy_price, sell_price):
        return sell_price / buy_price - 1

    def is_trade_profitable(self, rate, min_rate):
        return rate > min_rate
