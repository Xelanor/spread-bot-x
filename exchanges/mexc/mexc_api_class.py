import logging

from .utils import sign_request, request
from .mexc_api import (
    get_mexc_tickers,
    get_mexc_depth,
    get_mexc_product_details,
    get_allowed_symbols,
)
from tenacity import retry, stop, wait

logger = logging.getLogger(__name__)


class MexcAPI:
    def __init__(self, ticker, public_key, private_key, group=None, kyc=None):
        try:
            self.nominator = ticker.split("/")[0]
            self.denominator = ticker.split("/")[1]
            self.ticker = f"{self.nominator}{self.denominator}"
        except:
            self.ticker = ticker

        self.public_key = public_key
        self.private_key = private_key
        self.kyc = kyc

    def get_tickers(self):
        tickers = get_mexc_tickers()
        return tickers

    def get_depth(self):
        asks, bids = get_mexc_depth(self.ticker)
        return asks, bids

    def get_product_details(self):
        product_details = get_mexc_product_details(self.ticker)
        price_precision = product_details["quotePrecision"]
        price_precision = 1 / 10**price_precision
        quantity_precision = product_details["baseAssetPrecision"]
        quantity_precision = 1 / 10**quantity_precision
        return price_precision, quantity_precision

    def get_asset_details(self):
        url = "/api/v3/capital/config/getall"

        res = sign_request(self.public_key, self.private_key, "GET", url)
        details = {}

        for asset in res:
            coin = asset["coin"]
            network_list = asset["networkList"]
            details[coin] = []
            for network in network_list:
                network_name = network["netWork"]
                deposit_status = network["depositEnable"]
                withdraw_status = network["withdrawEnable"]
                withdraw_fee = network["withdrawFee"]
                details[coin].append(
                    {
                        "network": network_name,
                        "deposit_status": deposit_status,
                        "withdraw_status": withdraw_status,
                        "withdraw_fee": float(withdraw_fee),
                    }
                )

        return details

    def is_ticker_allowed(self):
        symbols = get_allowed_symbols()
        return self.ticker in symbols

    def create_limit_order(self, side, price, quantity):
        url = "/api/v3/order"

        params = {
            "symbol": self.ticker,
            "side": "BUY" if side == "buy" else "SELL",
            "type": "LIMIT",
            "price": price,
            "quantity": quantity,
        }
        res = sign_request(self.public_key, self.private_key, "POST", url, params)

        if "orderId" not in res:
            return None, res

        return res["orderId"], res

    def create_market_order(self, side, price, quantity):
        url = "/api/v3/order"

        params = {
            "symbol": self.ticker,
            "side": "BUY" if side == "buy" else "SELL",
            "type": "MARKET",
        }
        if side == "buy":
            params["quoteOrderQty"] = price * quantity
        elif side == "sell":
            params["quantity"] = quantity

        res = sign_request(self.public_key, self.private_key, "POST", url, params)

        if "orderId" not in res:
            return None, res

        return res["orderId"], res

    @retry(stop=stop.stop_after_attempt(2), wait=wait.wait_fixed(0.7))
    def get_order_status(self, order_id):
        url = "/api/v3/order"

        params = {"symbol": self.ticker, "orderId": order_id}
        res = sign_request(self.public_key, self.private_key, "GET", url, params)
        try:
            filled_price = float(res["cummulativeQuoteQty"]) / float(res["executedQty"])
            filled_quantity = float(res["executedQty"])
        except ZeroDivisionError:
            filled_price = 0
            filled_quantity = 0
        except KeyError:
            logger.error(f"Error in mexc get_order_status: {res}")
            raise Exception("Error in mexc get_order_status: Try Again")

        """
        Doğru fiyat cummulativeQuoteQty / executedQty
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
        url = "/api/v3/order"

        params = {"symbol": self.ticker, "orderId": order_id}
        res = sign_request(self.public_key, self.private_key, "DELETE", url, params)

        if "code" in res:
            return False, res

        return True, res

    def get_account_balance_function(self):
        url = "/api/v3/account"
        res = sign_request(self.public_key, self.private_key, "GET", url)
        balances = res["balances"]
        return balances

    def get_account_balance(self, coins=None):
        _balances = self.get_account_balance_function()
        account_balance = {}

        for balance in _balances:
            ticker = balance["asset"]
            available = float(balance["free"])
            frozen = float(balance["locked"])
            total = available + frozen

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
        url = "/api/v3/userDataStream"
        res = sign_request(self.public_key, self.private_key, "POST", url)
        listen_key = res["listenKey"]

        return listen_key

    def cancel_open_orders(self):
        url = "/api/v3/openOrders"
        params = {"symbol": self.ticker}
        res = sign_request(self.public_key, self.private_key, "DELETE", url, params)
        return res

    def get_deposits(self):
        url = "/api/v3/capital/deposit/hisrec"
        res = sign_request(self.public_key, self.private_key, "GET", url)
        deposits = {}
        for deposit in res:
            coin = deposit["coin"]
            if coin not in deposits:
                deposits[coin] = []

            amount = float(deposit["amount"])
            network = deposit["network"]
            date = deposit["insertTime"]

            deposits[coin].append({"amount": amount, "network": network, "date": date})

        return deposits

    def get_withdrawals(self):
        url = "/api/v3/capital/withdraw/history"
        res = sign_request(self.public_key, self.private_key, "GET", url)
        return res

    def get_withdraw_adresses(self):
        url = "/api/v3/capital/withdraw/address"
        res = sign_request(self.public_key, self.private_key, "GET", url)
        return res["data"]

    def get_deposit_adresses(self, chain):
        url = "/api/v3/capital/deposit/address"
        params = {
            "coin": self.nominator,
        }
        res = sign_request(self.public_key, self.private_key, "GET", url, params)
        return res

    def withdraw_request(self, network, address, amount):
        url = "/api/v3/capital/withdraw/apply"

        params = {
            "coin": self.nominator,
            "network": network,
            "address": address,
            "amount": str(amount),
        }
        res = sign_request(self.public_key, self.private_key, "POST", url, params)
        if "code" in res:
            return False, None, res

        return True, res["id"], res
