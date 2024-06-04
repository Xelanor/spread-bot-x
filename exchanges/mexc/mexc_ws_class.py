import asyncio
import websockets
import json
import traceback

from exchanges.mexc.utils import WS_HOST
from exchanges.mexc.mexc_api_class import MexcAPI


class MexcWS:
    def __init__(
        self, ticker=None, public_key=None, private_key=None, group=None, kyc=None
    ):
        self.ticker = ticker
        if ticker:
            self.tick = ticker.split("/")[0]
        self.public_key = public_key
        self.private_key = private_key
        self.group = group
        self.kyc = kyc

    async def on_message(self, message, depth=None, balance=None):
        message = json.loads(message)
        try:
            if "depth" in message["c"]:
                asks = message["d"]["asks"]
                bids = message["d"]["bids"]
                asks = [[ask["p"], ask["v"]] for ask in asks]
                bids = [[bid["p"], bid["v"]] for bid in bids]
                depth("Mexc", asks, bids)
            elif "account" in message["c"]:
                tick = message["d"]["a"]
                self.account_balance[tick] = {
                    "available": float(message["d"]["f"]),
                    "frozen": float(message["d"]["l"]),
                    "total": float(message["d"]["f"]) + float(message["d"]["l"]),
                }
                balance("Mexc", self.kyc, self.account_balance)
        except:
            print("Received message:", message)

    async def main(self, depth=None, balance=None):
        Mexc = MexcAPI(
            self.ticker, self.public_key, self.private_key, self.group, self.kyc
        )
        listen_key = Mexc.create_ws_listen_key()
        key = f"?listenKey={listen_key}"

        if depth:
            params = json.dumps(
                {
                    "method": "SUBSCRIPTION",
                    "params": [
                        f"spot@public.limit.depth.v3.api@{self.tick}USDT@5",
                    ],
                }
            )

        if balance:
            self.account_balance = Mexc.get_account_balance()
            balance(
                "Mexc", self.kyc, self.account_balance
            )  # Send initial account balance
            params = json.dumps(
                {
                    "method": "SUBSCRIPTION",
                    "params": [
                        "spot@private.account.v3.api",
                    ],
                }
            )
        try:
            async with websockets.connect(WS_HOST + key) as websocket:
                await websocket.send(params)
                while True:
                    message = await websocket.recv()
                    await self.on_message(message, depth=depth, balance=balance)
        except (
            websockets.exceptions.ConnectionClosed,
            websockets.exceptions.InvalidHandshake,
        ):

            print("Mexc Connection closed, restarting...")
            print(traceback.format_exc())
            await self.main(depth=depth, balance=balance)
