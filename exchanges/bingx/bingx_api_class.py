import logging
import requests
from tenacity import retry, stop, wait
from django.core.cache import cache
from app.celery import app

from exchanges.bingx.utils import sign_request
from exchanges.bingx.bingx_api import (
    get_tickers,
    get_depth,
    get_product_details,
    get_allowed_symbols,
)

logger = logging.getLogger(__name__)


def telegram_bot_sendtext(bot_message):
    bot_token = "5687151976:AAF94-ghuVdi3yBxDYwYzPC_MOHrM7D40pg"
    bot_chatID = "-1002000333988"
    send_text = (
        "https://api.telegram.org/bot"
        + bot_token
        + "/sendMessage?chat_id="
        + bot_chatID
        + "&parse_mode=Markdown&text="
        + bot_message
    )
    response = requests.get(send_text)
    return response.json()


def req_is_limited(key, limit, period):
    if cache.set(key, limit, nx=True):
        cache.expire(key, period)
    cached_val = cache.get(key)
    if cached_val and cached_val > 0:
        cache.decr(key, 1)
        return False
    return True


class BingXAPI:
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
        price_precision = product_details["tickSize"]
        quantity_precision = product_details["stepSize"]
        return price_precision, quantity_precision

    def is_ticker_allowed(self):
        symbols = get_allowed_symbols()
        return self.ticker in symbols

    def get_asset_details(self):
        url = "/openApi/wallets/v1/capital/config/getall"

        res = sign_request(self.public_key, self.private_key, self.group, "GET", url)
        if res["code"] != 0:
            logger.error(f"Bingx get_asset_details, error in response. {res}")
            return {}

        res = res["data"]
        details = {}

        for asset in res:
            coin = asset["coin"]
            network_list = asset["networkList"]
            details[coin] = []
            for network in network_list:
                network_name = network["network"]
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

    @retry(stop=stop.stop_after_attempt(2), wait=wait.wait_fixed(0.5))
    def create_limit_order(self, side, price, quantity):
        # Check rate limit
        key = f"Bingx_create_limit_order_{self.kyc}"
        limit = 4
        period = 1

        if req_is_limited(key, limit, period):
            logger.warning(
                f"Bingx create limit order Rate limit exceeded trying again."
            )
            raise Exception("Bingx create limit order Rate limit exceeded")

        url = "/openApi/spot/v1/trade/order"

        params = {
            "symbol": self.ticker,
            "side": "BUY" if side == "buy" else "SELL",
            "type": "LIMIT",
            "price": str(price),
            "quantity": str(quantity),
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        if res["code"] == 100410 and res["msg"] == "rate limited":
            logger.error("Bingx create limit order rate limit exceeded")
            cache.set("Bingx_rate_limit_exceeded", True, timeout=310)
            telegram_bot_sendtext(f"Bingx-{self.kyc} order rate limit exceeded")

        if res["code"] != 0:
            return None, res

        return res["data"]["orderId"], res

    def create_market_order(self, side, price, quantity):
        url = "/openApi/spot/v1/trade/order"

        params = {
            "symbol": self.ticker,
            "side": "BUY" if side == "buy" else "SELL",
            "type": "MARKET",
            "quantity": str(quantity),
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        if res["code"] != 0:
            return None, res

        return res["data"]["orderId"], res

    @retry(
        stop=stop.stop_after_attempt(5),
        wait=wait.wait_fixed(0.3) + wait.wait_random(0.2, 1.2),
    )
    def get_order_status(self, order_id):
        key = f"Bingx_get_order_status_{self.kyc}"
        limit = 7
        period = 1

        if req_is_limited(key, limit, period):
            logger.warning(f"Bingx get order status Rate limit exceeded trying again.")
            raise Exception("Bingx get order status Rate limit exceeded")

        url = "/openApi/spot/v1/trade/query"

        params = {"symbol": self.ticker, "orderId": order_id}
        res = sign_request(
            self.public_key, self.private_key, self.group, "GET", url, params
        )
        if res["code"] == 100410 and res["msg"] == "rate limited":
            logger.error("Bingx order status rate limit exceeded")
            cache.set("Bingx_rate_limit_exceeded", True, timeout=310)
            telegram_bot_sendtext(f"Bingx-{self.kyc} order status rate limit exceeded")

        if res["code"] != 0:
            logger.error(f"Bingx get_order_status, error in response. {res}")

        res = res["data"]
        try:
            filled_price = float(res["cummulativeQuoteQty"]) / float(res["executedQty"])
        except ZeroDivisionError:
            filled_price = 0
        filled_quantity = float(res["executedQty"])

        """
        Doğru fiyat cummulativeQuoteQty / executedQty
        {
            "symbol": "BTC-USDT",
            "orderId": 1788928349750329344,
            "price": "62940.51",
            "StopPrice": "0",
            "origQty": "0.00019",
            "executedQty": "0.00019",
            "cummulativeQuoteQty": "11.958671629523028",
            "status": "FILLED",
            "type": "MARKET",
            "side": "SELL",
            "time": 1715348729918,
            "updateTime": 1715348729935,
            "origQuoteOrderQty": "0",
            "fee": "-0.011958671629523028",
            "feeAsset": "USDT",
            "clientOrderID": "",
        }
        """
        return filled_price, filled_quantity, res

    def cancel_order(self, order_id):
        url = "/openApi/spot/v1/trade/cancel"

        params = {"symbol": self.ticker, "orderId": order_id}
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        if res["code"] != 0:
            return False, res

        return True, res

    def get_account_balance_function(self):
        key = f"Bingx_get_account_balance_{self.kyc}"
        limit = 4
        period = 1

        if req_is_limited(key, limit, period):
            logger.warning(
                f"Bingx get account balance Rate limit exceeded trying again."
            )
            raise Exception("Bingx get account balance Rate limit exceeded")

        url = "/openApi/spot/v1/account/balance"
        res = sign_request(self.public_key, self.private_key, self.group, "GET", url)
        balances = res["data"]["balances"]
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

    @retry(stop=stop.stop_after_attempt(5), wait=wait.wait_fixed(1))
    def cancel_open_orders(self):
        # Check rate limit
        key = f"Bingx_cancel_open_orders_{self.kyc}"
        limit = 2
        period = 1

        if req_is_limited(key, limit, period):
            logger.warning(
                f"Bingx cancel open orders Rate limit exceeded trying again."
            )
            raise Exception("Bingx cancel open orders Rate limit exceeded")

        url = "/openApi/spot/v1/trade/cancelOpenOrders"

        params = {"symbol": self.ticker}
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        return res

    def create_ws_listen_key(self):
        url = "/openApi/user/auth/userDataStream"

        res = sign_request(self.public_key, self.private_key, self.group, "POST", url)
        res = res["listenKey"]

        return res

    def get_deposits(self):
        url = "/openApi/api/v3/capital/deposit/hisrec"
        res = sign_request(self.public_key, self.private_key, self.group, "GET", url)
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
        url = "/openApi/api/v3/capital/withdraw/history"
        res = sign_request(self.public_key, self.private_key, self.group, "GET", url)
        return res

    def get_deposit_adresses(self, chain):
        url = "/openApi/wallets/v1/capital/deposit/address"
        params = {
            "coin": self.nominator,
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "GET", url, params
        )
        return res["data"]["data"]

    def withdraw_request(self, network, address, amount):
        url = "/openApi/wallets/v1/capital/withdraw/apply"

        params = {
            "coin": self.nominator,
            "network": network,
            "address": address,
            "amount": str(amount),
            "walletType": 1,
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )
        if res["code"] != 0:
            return False, None, res

        return True, res["data"]["id"], res

    def get_open_orders(self):
        url = "/openApi/spot/v1/trade/openOrders"
        res = sign_request(self.public_key, self.private_key, self.group, "GET", url)
        return res["data"]["orders"]
