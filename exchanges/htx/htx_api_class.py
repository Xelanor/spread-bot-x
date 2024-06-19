import logging
import time

from .htx_api import get_tickers, get_depth, get_product_details
from .utils import request, sign_request

logger = logging.getLogger(__name__)


class HtxAPI:
    def __init__(self, ticker, public_key, private_key, group=None, kyc=None):
        try:
            self.nominator = ticker.split("/")[0].lower()
            self.denominator = ticker.split("/")[1].lower()
            self.ticker = f"{self.nominator}{self.denominator}"
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
        price_precision = float(product_details["tpp"])
        price_precision = 1 / 10**price_precision
        quantity_precision = float(product_details["tap"])
        quantity_precision = 1 / 10**quantity_precision
        return price_precision, quantity_precision

    def get_asset_details(self):
        url = "/v2/reference/currencies"

        res = request("GET", url)
        res = res["data"]
        details = {}

        for asset in res:
            coin = asset["currency"].upper()
            network_list = asset["chains"]
            details[coin] = []
            for network in network_list:
                network_name = network["chain"]
                deposit_status = (
                    True if network["depositStatus"] == "allowed" else False
                )
                withdraw_status = (
                    True if network["withdrawStatus"] == "allowed" else False
                )
                withdraw_fee = (
                    float(network["transactFeeWithdraw"])
                    if network["withdrawFeeType"] == "fixed"
                    else None
                )
                details[coin].append(
                    {
                        "network": network_name,
                        "deposit_status": deposit_status,
                        "withdraw_status": withdraw_status,
                        "withdraw_fee": withdraw_fee,
                    }
                )

        return details

    def get_accounts(self):
        url = "/v1/account/accounts"
        res = sign_request(self.public_key, self.private_key, "GET", url)
        balances = res["data"]
        return balances

    def get_account_balance_function(self):
        url = "/v1/account/accounts/32213981/balance"
        res = sign_request(self.public_key, self.private_key, "GET", url)
        balances = res["data"]["list"]
        return balances

    def get_account_balance(self, coins=None):
        _balances = self.get_account_balance_function()
        account_balance = {}

        for balance in _balances:
            ticker = balance["currency"].upper()
            if ticker not in account_balance:
                account_balance[ticker] = {}

            if balance["type"] == "trade":
                available = float(balance["balance"])
                account_balance[ticker]["available"] = available

            if balance["type"] == "frozen":
                frozen = float(balance["balance"])
                account_balance[ticker]["frozen"] = frozen

        for ticker in account_balance:
            account_balance[ticker]["total"] = (
                account_balance[ticker]["available"] + account_balance[ticker]["frozen"]
            )

        for ticker in account_balance.copy():
            if account_balance[ticker]["total"] == 0:
                del account_balance[ticker]

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
        url = "/v1/order/orders/place"

        data = {
            "account-id": "32213981",
            "symbol": self.ticker,
            "type": "buy-limit" if side == "buy" else "sell-limit",
            "price": price,
            "amount": quantity,
        }
        res = sign_request(self.public_key, self.private_key, "POST", url, data=data)
        if res["status"] != "ok":
            return None, res

        return res["data"], res

    def create_market_order(self, side, price, quantity):
        pass

    def get_order_status(self, order_id):
        url = f"/v1/order/orders/{order_id}"

        res = sign_request(self.public_key, self.private_key, "GET", url)

        if res["status"] != "ok":
            logger.error(f"HTX order status failed for order_id: {order_id}")

        res = res["data"]
        try:
            filled_price = float(res["field-cash-amount"]) / float(res["field-amount"])
        except ZeroDivisionError:
            filled_price = 0
        filled_quantity = float(res["field-amount"])

        """
        {
            "status": "ok",
            "data": {
                "id": 1088316123910612,
                "symbol": "btcusdt",
                "amount": "0.000333",
                "market-amount": "0",
                "price": "70000",
                "created-at": 1718349813185,
                "type": "buy-limit",
                "field-amount": "0.000333",
                "field-cash-amount": "22.31062704",
                "field-fees": "0.000000666",
            },
        }
        """
        return filled_price, filled_quantity, res

    def cancel_order(self, order_id):
        url = f"/v1/order/orders/{order_id}/submitcancel"

        res = sign_request(self.public_key, self.private_key, "POST", url)

        if res["status"] != "ok":
            return False, res

        return True, res

    def cancel_open_orders(self):
        url = "/v1/order/orders/batchCancelOpenOrders"

        params = {"symbol": self.ticker}
        res = sign_request(self.public_key, self.private_key, "POST", url, params)
        return res

    def get_deposits(self):
        url = "/v1/query/deposit-withdraw"
        params = {"type": "deposit"}
        res = sign_request(self.public_key, self.private_key, "GET", url, params=params)

        deposits = {}
        for deposit in res["data"]:
            coin = deposit["currency"].upper()
            if coin not in deposits:
                deposits[coin] = []

            amount = float(deposit["amount"])
            network = deposit["chain"]
            date = deposit["created-at"]

            deposits[coin].append({"amount": amount, "network": network, "date": date})

        return deposits

    def get_deposit_adresses(self, chain):
        url = "/v2/account/deposit/address"
        params = {
            "currency": self.nominator,
        }
        res = sign_request(self.public_key, self.private_key, "GET", url, params)
        networks = []
        for network in res["data"]:
            networks.append(
                {"network": network["chain"], "address": network["address"]}
            )

        return networks

    def withdraw_request(self, network, address, amount):
        url = "/v1/dw/withdraw/api/create"

        data = {
            "currency": self.nominator,
            "chain": network,
            "address": address,
            "amount": amount,
        }
        res = sign_request(self.public_key, self.private_key, "POST", url, data=data)
        if res["status"] != "ok":
            return False, None, res

        return True, res["data"], res


# api = HtxAPI(
#     "USDT/USDT",
#     "cf5994d9-da9d62a1-bvrge3rf7j-b4d71",
#     "5381db71-945fbbfb-68068d79-5f878",
#     "maker",
#     "kyc",
# )
# print(api.create_limit_order("buy", 50000, 0.000333))
# print(api.withdraw_request("trc20usdt", "THXcyciu1HPGmUsTBbXJdJG2nqxNSsrT8b", "70"))
# print(api.get_account_balance("USDT"))
# print(api.get_account_balance())
# # print(api.get_account_balance("USDT"))
