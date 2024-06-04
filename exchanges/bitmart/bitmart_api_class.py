from tenacity import retry, stop, wait
import logging

from .utils import sign_request, request
from .bitmart_api import (
    get_bitmart_tickers,
    get_bitmart_depth,
    get_bitmart_product_details,
)

logger = logging.getLogger(__name__)


class BitmartAPI:
    def __init__(self, ticker, public_key, private_key, group=None, kyc=None):
        try:
            self.nominator = ticker.split("/")[0]
            self.denominator = ticker.split("/")[1]
            self.ticker = f"{self.nominator}_{self.denominator}"
        except:
            self.ticker = ticker

        self.public_key = public_key
        self.private_key = private_key
        self.group = group
        self.kyc = kyc

    def get_tickers(self):
        tickers = get_bitmart_tickers()
        return tickers

    def get_depth(self):
        asks, bids = get_bitmart_depth(self.ticker)
        return asks, bids

    @retry(stop=stop.stop_after_attempt(20), wait=wait.wait_fixed(2))
    def get_product_details(self):
        product_details = get_bitmart_product_details(self.ticker)
        price_precision = float(product_details["price_max_precision"])
        price_precision = 1 / 10**price_precision
        quantity_precision = product_details["quote_increment"]
        quantity_precision = float(quantity_precision)
        return price_precision, quantity_precision

    def get_asset_details(self):
        url = "/spot/v1/currencies"

        res = request("GET", url)
        res = res["data"]["currencies"]

        details = {}
        for asset in res:
            coin = asset["id"]
            details[coin] = []

            network_name = None
            deposit_status = asset["deposit_enabled"]
            withdraw_status = asset["withdraw_enabled"]
            withdraw_fee = None
            details[coin].append(
                {
                    "network": network_name,
                    "deposit_status": deposit_status,
                    "withdraw_status": withdraw_status,
                    "withdraw_fee": withdraw_fee,
                }
            )

        return details

    def get_account_balance_function(self):
        url = "/spot/v1/wallet"
        res = sign_request(self.public_key, self.private_key, self.group, "GET", url)
        balances = res["data"]["wallet"]
        return balances

    def get_account_balance(self, coins=None):
        _balances = self.get_account_balance_function()
        account_balance = {}

        for balance in _balances:
            ticker = balance["id"]
            available = float(balance["available"])
            frozen = float(balance["frozen"])
            total = float(balance["total"])

            if total > 0:
                account_balance[ticker] = {
                    "total": total,
                    "available": available,
                    "frozen": frozen,
                }

        result = {}
        if coins is None:  #  Retreive all coins
            result = account_balance

        elif isinstance(coins, list):  #  Retreive specific coins
            for coin in coins:
                if coin in account_balance:
                    result[coin] = account_balance[coin]

        elif isinstance(coins, str):  #  Retreive a single coin
            if coins in account_balance:
                result[coins] = account_balance[coins]

        else:
            raise ValueError(
                "Invalid input for coins. Please provide a string or a list."
            )

        return result

    def create_limit_order(self, side, price, quantity):
        url = "/spot/v2/submit_order"

        params = {
            "symbol": self.ticker,
            "side": "buy" if side == "buy" else "sell",
            "type": "limit",
            "price": price,
            "size": quantity,
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )
        if res["code"] != 1000:
            return None, res

        return res["data"]["order_id"], res

    def create_market_order(self, side, price, quantity):
        url = "/spot/v2/submit_order"

        params = {
            "symbol": self.ticker,
            "side": "buy" if side == "buy" else "sell",
            "type": "market",
        }
        if side == "buy":
            params["notional"] = price * quantity
        elif side == "sell":
            params["size"] = quantity

        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )
        if res["code"] != 1000:
            return None, res

        return res["data"]["order_id"], res

    def get_order_status(self, order_id):
        url = "/spot/v4/query/order"

        params = {"orderId": order_id}
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )
        res = res["data"]
        filled_price = float(res["priceAvg"])
        filled_quantity = float(res["filledSize"])

        """
        {'code': 1000,
        'data': {'orderId': '255971512459182589',
        'symbol': 'SOL_USDT',
        'side': 'sell',
        'type': 'market',
        'state': 'filled',
        'priceAvg': '141.3662',
        'filledSize': '0.08',
        'filledNotional': '11.30929600',
        'updateTime': 1714306076995}}
        """

        return filled_price, filled_quantity, res

    @retry(stop=stop.stop_after_attempt(3), wait=wait.wait_fixed(2))
    def cancel_order(self, order_id):
        url = "/spot/v3/cancel_order"

        params = {"symbol": self.ticker, "order_id": order_id}
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        if res["code"] == 50031:
            logger.debug(f"Order already completed: {res}")
            return True, res

        if res["code"] == 50030:
            logger.debug(f"Order already cancelled: {res}")
            return True, res

        if res["code"] != 1000:
            logger.error(f"Failed to cancel order: {res}")
            raise Exception

        return True, res

    @retry(stop=stop.stop_after_attempt(60), wait=wait.wait_fixed(1))
    def cancel_open_orders(self):
        url = "/spot/v1/cancel_orders"

        params = {"symbol": self.ticker}
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        if res["code"] != 1000:
            raise Exception

        return res
