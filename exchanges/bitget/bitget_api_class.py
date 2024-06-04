import logging
import time

from .bitget_api import get_tickers, get_depth, get_product_details
from .utils import sign_request, request

logger = logging.getLogger(__name__)


class BitgetAPI:
    def __init__(self, ticker, public_key, private_key, group=None, kyc=None):
        try:
            self.nominator = ticker.split("/")[0]
            self.denominator = ticker.split("/")[1]
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
        price_precision = float(product_details["pricePrecision"])
        price_precision = 1 / 10**price_precision
        quantity_precision = float(product_details["quantityPrecision"])
        quantity_precision = 1 / 10**quantity_precision
        return price_precision, quantity_precision

    def get_asset_details(self):
        url = "/api/v2/spot/public/coins"

        res = request("GET", url)
        res = res["data"]
        details = {}

        for asset in res:
            coin = asset["coin"]
            network_list = asset["chains"]
            details[coin] = []
            for network in network_list:
                network_name = network["chain"]
                deposit_status = True if network["rechargeable"] == "true" else False
                withdraw_status = True if network["withdrawable"] == "true" else False
                withdraw_fee = float(network["withdrawFee"]) + float(
                    network["extraWithdrawFee"]
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

    def create_limit_order(self, side, price, quantity):
        url = "/api/v2/spot/trade/place-order"

        params = {
            "symbol": self.ticker,
            "side": "Buy" if side == "buy" else "Sell",
            "orderType": "limit",
            "force": "GTC",
            "price": str(price),
            "size": str(quantity),
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )
        if res["code"] != "00000":
            return None, res

        return res["data"]["orderId"], res

    def create_market_order(self, side, price, quantity):
        pass

    def get_order_status(self, order_id):
        url = "/api/v2/spot/trade/orderInfo"

        params = {"orderId": order_id}
        res = sign_request(
            self.public_key, self.private_key, self.group, "GET", url, params
        )

        if res["code"] != "00000":
            logger.error(f"Bitget order status failed for order_id: {order_id}")

        res = res["data"][0]
        filled_price = float(res["priceAvg"])
        filled_quantity = float(res["baseVolume"])

        return filled_price, filled_quantity, res

    def cancel_order(self, order_id):
        url = "/api/v2/spot/trade/cancel-order"

        params = {"symbol": self.ticker, "orderId": order_id}
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        if res["code"] != "00000":
            return False, res

        return True, res

    def get_account_balance_function(self):
        url = "/api/v2/spot/account/assets"
        res = sign_request(self.public_key, self.private_key, self.group, "GET", url)
        balances = res["data"]
        return balances

    def get_account_balance(self, coins=None):
        _balances = self.get_account_balance_function()
        account_balance = {}

        for balance in _balances:
            ticker = balance["coin"]
            available = float(balance["available"])
            frozen = float(balance["frozen"])
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

    def cancel_open_orders(self):
        url = "/api/v2/spot/trade/cancel-symbol-order"

        params = {"symbol": self.ticker}
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        return res

    def get_deposits(self):
        url = "/api/v2/spot/wallet/deposit-records"
        # From 1 week ago to now
        start_time = (int(time.time()) - 604800) * 1000
        end_time = int(time.time()) * 1000
        params = {"limit": 100, "startTime": start_time, "endTime": end_time}
        res = sign_request(
            self.public_key, self.private_key, self.group, "GET", url, params
        )
        res = res["data"]
        deposits = {}
        for deposit in res:
            coin = deposit["coin"]
            if coin not in deposits:
                deposits[coin] = []

            amount = float(deposit["size"])
            network = deposit["chain"]
            date = int(deposit["cTime"])

            deposits[coin].append({"amount": amount, "network": network, "date": date})

        return deposits

    def get_deposit_adresses(self, chain):
        url = "/api/v2/spot/wallet/deposit-address"
        params = {"coin": self.nominator, "chain": chain}
        res = sign_request(
            self.public_key, self.private_key, self.group, "GET", url, params
        )

        if res["code"] != "00000":
            return []

        networks = []
        networks.append(
            {"network": res["data"]["chain"], "address": res["data"]["address"]}
        )

        return networks

    def withdraw_request(self, network, address, amount):
        url = "/api/v2/spot/wallet/withdrawal"

        params = {
            "coin": self.nominator,
            "transferType": "on_chain",
            "chain": network,
            "address": address,
            "size": str(amount),
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )
        if res["code"] != "00000":
            return False, None, res

        return True, res["data"]["orderId"], res


# api = BitgetAPI(
#     "USDT/USDT",
#     "bg_b0803ef4d69a7f5d9567d278ae4aba0e",
#     "a9fbb50ac864a5973be94fc27fbc5db93a75363e994925a9abb436cad4c7e3b8",
#     "makerbot",
#     "kyc",
# )
# # print(api.create_limit_order("sell", 0.02, 10000))
# print(api.get_deposit_adresses())
# # print(api.get_account_balance("USDT"))
