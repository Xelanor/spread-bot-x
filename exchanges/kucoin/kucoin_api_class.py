from uuid import uuid1

from .utils import sign_request, request
from .kucoin_api import get_product_details, get_tickers, get_depth


class KucoinAPI:
    def __init__(self, ticker, public_key, private_key, group=None, kyc=None):
        try:
            self.nominator = ticker.split("/")[0]
            self.denominator = ticker.split("/")[1]
            self.ticker = f"{self.nominator}-{self.denominator}"
        except:
            self.ticker = ticker

        self.public_key = public_key
        self.private_key = private_key
        self.group = group
        self.kyc = kyc

    def get_tickers(self):
        tickers = get_tickers()
        return tickers

    def get_depth(self):
        asks, bids = get_depth(self.ticker)
        return asks, bids

    def get_product_details(self):
        product_details = get_product_details(self.ticker)
        price_precision = float(product_details["priceIncrement"])
        quantity_precision = product_details["baseIncrement"]
        return price_precision, quantity_precision

    def create_limit_order(self, side, price, quantity):
        url = "/api/v1/orders"

        params = {
            "clientOid": "".join([each for each in str(uuid1()).split("-")]),
            "symbol": self.ticker,
            "side": "buy" if side == "buy" else "sell",
            "type": "limit",
            "price": str(price),
            "size": str(quantity),
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        if res["code"] != "200000":
            return None, res

        return res["data"]["orderId"], res

    def create_market_order(self, side, price, quantity):
        url = "/api/v1/orders"

        params = {
            "clientOid": "".join([each for each in str(uuid1()).split("-")]),
            "symbol": self.ticker,
            "side": "buy" if side == "buy" else "sell",
            "type": "market",
            "size": str(quantity),
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        if res["code"] != "200000":
            return None, res

        return res["data"]["orderId"], res

    def get_order_status(self, order_id):
        url = f"/api/v1/orders/{order_id}"

        res = sign_request(self.public_key, self.private_key, self.group, "GET", url)
        res = res["data"]
        try:
            filled_price = float(res["dealFunds"]) / float(res["dealSize"])
        except ZeroDivisionError:
            filled_price = 0
        filled_quantity = float(res["dealSize"])

        """
        Doğru fiyat dealFunds / dealSize
        {'symbol': 'SOLAMAUSDT',
        'orderId': 'C02__413169175276630018083',
        'executedQty': '190',
        'cummulativeQuoteQty': '5.282',
        'status': 'FILLED',
        'type': 'MARKET',
        'side': 'SELL'}
        """

        return filled_price, filled_quantity, res

    def cancel_order(self, order_id):
        url = f"/api/v1/orders/{order_id}"

        res = sign_request(self.public_key, self.private_key, self.group, "DELETE", url)

        if res["code"] != "200000":
            return False, res

        return True, res

    def get_account_balance_function(self):
        url = "/api/v1/accounts"
        res = sign_request(self.public_key, self.private_key, self.group, "GET", url)
        balances = res["data"]
        return balances

    def get_account_balance(self, coins=None):
        _balances = self.get_account_balance_function()
        account_balance = {}

        for balance in _balances:
            if balance["type"] != "trade":
                continue

            ticker = balance["currency"]
            total = float(balance["balance"])
            available = float(balance["available"])
            frozen = total - available

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

    def create_ws_listen_key(self):
        url = "/api/v1/bullet-private"
        res = sign_request(self.public_key, self.private_key, self.group, "POST", url)
        token = res["data"]["token"]
        endpoint = res["data"]["instanceServers"][0]["endpoint"]
        return token, endpoint

    def cancel_open_orders(self):
        url = "/api/v1/orders"

        params = {"symbol": self.ticker}
        res = sign_request(
            self.public_key, self.private_key, self.group, "DELETE", url, params
        )

        return res
