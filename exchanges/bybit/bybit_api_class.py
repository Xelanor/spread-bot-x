import logging
import time
from uuid import uuid4

# from tenacity import retry, stop, wait

from exchanges.bybit.utils import sign_request
from exchanges.bybit.bybit_api import get_tickers, get_depth, get_product_details

logger = logging.getLogger(__name__)


class BybitAPI:
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
        price_precision = float(product_details["priceFilter"]["tickSize"])
        quantity_precision = float(product_details["lotSizeFilter"]["basePrecision"])
        return price_precision, quantity_precision

    def get_asset_details(self):
        url = "/v5/asset/coin/query-info"

        res = sign_request(self.public_key, self.private_key, self.group, "GET", url)
        res = res["result"]["rows"]
        details = {}

        for asset in res:
            coin = asset["coin"]
            network_list = asset["chains"]
            details[coin] = []
            for network in network_list:
                network_name = network["chainType"]
                deposit_status = True if network["chainDeposit"] == "1" else False
                withdraw_status = True if network["chainWithdraw"] == "1" else False
                withdraw_fee = network["withdrawFee"]
                if withdraw_fee == "":
                    withdraw_fee = 0

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
        url = "/v5/order/create"

        params = {
            "category": "spot",
            "symbol": self.ticker,
            "side": "Buy" if side == "buy" else "Sell",
            "orderType": "Limit",
            "price": str(price),
            "qty": str(quantity),
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )
        if res["retCode"] != 0:
            return None, res

        return res["result"]["orderId"], res

    def create_market_order(self, side, price, quantity):
        pass

    def get_order_status(self, order_id):
        url = "/v5/order/realtime"

        params = {"category": "spot", "orderId": order_id}
        res = sign_request(
            self.public_key, self.private_key, self.group, "GET", url, params
        )

        if res["retCode"] != 0:
            logger.error(f"Bybit order status failed for order_id: {order_id}")

        res = res["result"]["list"][0]
        filled_price = float(res["avgPrice"])
        filled_quantity = float(res["cumExecQty"])

        return filled_price, filled_quantity, res

    def cancel_order(self, order_id):
        url = "/v5/order/cancel"

        params = {"category": "spot", "symbol": self.ticker, "orderId": order_id}
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        if res["retCode"] != 0:
            return False, res

        return True, res

    def get_account_balance_function(self):
        url = "/v5/account/wallet-balance"
        params = {"accountType": "UNIFIED"}
        res = sign_request(
            self.public_key, self.private_key, self.group, "GET", url, params
        )
        balances = res["result"]["list"][0]["coin"]
        return balances

    def get_account_balance(self, coins=None):
        _balances = self.get_account_balance_function()
        account_balance = {}

        for balance in _balances:
            ticker = balance["coin"]
            frozen = float(balance["locked"])
            total = float(balance["walletBalance"])
            available = total - frozen

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
        url = "/v5/order/cancel-all"

        params = {"category": "spot", "symbol": self.ticker}
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )

        return res

    def get_deposits(self):
        url = "/v5/asset/deposit/query-record"
        res = sign_request(self.public_key, self.private_key, self.group, "GET", url)
        res = res["result"]["rows"]
        deposits = {}
        for deposit in res:
            coin = deposit["coin"]
            if coin not in deposits:
                deposits[coin] = []

            amount = float(deposit["amount"])
            network = deposit["chain"]
            date = int(deposit["successAt"])

            deposits[coin].append({"amount": amount, "network": network, "date": date})

        return deposits

    def get_deposit_adresses(self, chain):
        url = "/v5/asset/deposit/query-address"
        params = {
            "coin": self.nominator,
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "GET", url, params
        )
        if res["retCode"] != 0:
            logger.error(f"Bybit deposit address failed for coin: {self.nominator}")
            return False

        networks = []
        for network in res["result"]["chains"]:
            networks.append(
                {"network": network["chain"], "address": network["addressDeposit"]}
            )

        return networks

    def internal_transfer(self, amount):
        url = "/v5/asset/transfer/inter-transfer"

        uid = str(uuid4()).replace("-", "")
        params = {
            "transferId": uid,
            "coin": self.nominator,
            "amount": str(amount),
            "fromAccountType": "UNIFIED",
            "toAccountType": "FUND",
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )
        return res

    def withdraw_request(self, network, address, amount):
        url = "/v5/asset/withdraw/create"

        int_transfer = self.internal_transfer(amount)
        if int_transfer["retCode"] != 0:
            return False, None, int_transfer

        timestamp = int(time.time() * 10**3)
        params = {
            "coin": self.nominator,
            "chain": network,
            "address": address,
            "amount": str(amount),
            "accountType": "FUND",
            "feeType": 1,
            "timestamp": timestamp,
        }
        res = sign_request(
            self.public_key, self.private_key, self.group, "POST", url, params
        )
        if res["retCode"] != 0:
            return False, None, res

        transfer_id = res["result"]["id"]
        return True, transfer_id, res
