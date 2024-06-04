import logging
import time

from .xt_api import get_tickers, get_depth, get_product_details
from .utils import sign_request


class XtAPI:
    def __init__(self, ticker, public_key, private_key, group=None, kyc=None):
        try:
            self.nominator = ticker.split("/")[0].lower()
            self.denominator = ticker.split("/")[1].lower()
            self.ticker = f"{self.nominator}_{self.denominator}"
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
        price_precision = float(product_details["pricePrecision"])
        price_precision = 1 / 10**price_precision
        quantity_precision = float(product_details["quantityPrecision"])
        quantity_precision = 1 / 10**quantity_precision
        return price_precision, quantity_precision

    def get_account_balance_function(self):
        url = "/v4/balances"
        res = sign_request(self.public_key, self.private_key, "GET", url)
        balances = res["result"]["assets"]
        return balances

    def get_account_balance(self, coins=None):
        _balances = self.get_account_balance_function()
        account_balance = {}

        for balance in _balances:
            ticker = balance["currency"].upper()
            available = float(balance["availableAmount"])
            frozen = float(balance["frozenAmount"])
            total = float(balance["totalAmount"])

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
        url = "/v4/order"

        params = {
            "symbol": self.ticker,
            "side": "BUY" if side == "buy" else "SELL",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "bizType": "SPOT",
            "price": str(price),
            "quantity": str(quantity),
        }
        res = sign_request(self.public_key, self.private_key, "POST", url, json=params)
        if res["rc"] != 0:
            return None, res

        return res["result"]["orderId"], res

    def create_market_order(self, side, price, quantity):
        pass

    def get_order_status(self, order_id):
        url = f"/v4/order/{order_id}"

        res = sign_request(self.public_key, self.private_key, "GET", url)
        res = res["result"]
        filled_quantity = float(res["executedQty"])
        if filled_quantity == 0:
            return 0, 0, res
        filled_price = float(res["avgPrice"])

        return filled_price, filled_quantity, res

    def cancel_order(self, order_id):
        url = f"/v4/order/{order_id}"

        res = sign_request(self.public_key, self.private_key, "DELETE", url)

        if res["rc"] != 0:
            return False, res

        return True, res

    def get_asset_details(self):
        url = "/v4/public/wallet/support/currency"

        res = sign_request(self.public_key, self.private_key, "GET", url)
        res = res["result"]
        details = {}

        for asset in res:
            coin = asset["currency"].upper()
            network_list = asset["supportChains"]
            details[coin] = []
            for network in network_list:
                network_name = network["chain"]
                deposit_status = network["depositEnabled"]
                withdraw_status = network["withdrawEnabled"]
                withdraw_fee = float(network["withdrawFeeAmount"]) + float(
                    network["depositFeeRate"]
                )
                details[coin].append(
                    {
                        "network": network_name,
                        "deposit_status": deposit_status,
                        "withdraw_status": withdraw_status,
                        "withdraw_fee": float(withdraw_fee),
                    }
                )

        return details

    def cancel_open_orders(self):
        url = "/v4/open-order"

        params = {"symbol": self.ticker}
        res = sign_request(
            self.public_key, self.private_key, "DELETE", url, json=params
        )

        return res

    def get_deposits(self):
        url = "/v4/deposit/history"
        params = {"limit": 200}
        res = sign_request(self.public_key, self.private_key, "GET", url)
        res = res["result"]["items"]
        deposits = {}
        for deposit in res:
            coin = deposit["currency"].upper()
            if coin not in deposits:
                deposits[coin] = []

            amount = float(deposit["amount"])
            network = deposit["chain"]
            date = deposit["createdTime"]

            deposits[coin].append({"amount": amount, "network": network, "date": date})

        return deposits

    def get_deposit_adresses(self, chain):
        url = "/v4/deposit/address"
        params = {"currency": self.nominator, "chain": chain}
        res = sign_request(self.public_key, self.private_key, "GET", url, params=params)

        if res["rc"] != 0:
            return []

        networks = []
        networks.append({"network": chain, "address": res["result"]["address"]})
        return networks

    def withdraw_request(self, network, address, amount):
        url = "/v4/withdraw"

        params = {
            "currency": self.nominator,
            "chain": network,
            "address": address,
            "amount": amount,
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )
        if res["rc"] != 0:
            return False, None, res

        return True, res["result"]["id"], res


# api = XtAPI(
#     "USDT/USDT",
#     "a862725b-f10b-4d09-966f-b844686d65f3",
#     "5395d6b8473cf99137b95b78ce9804d1302fa3fd",
#     "maker",
#     "Berke",
# )
# print(api.get_account_balance("USDT"))
# print(api.create_limit_order("buy", 3.485, 27))
# print(api.get_order_status("367582205005916736"))
# print(api.get_deposit_adresses("SOL-SOL"))
