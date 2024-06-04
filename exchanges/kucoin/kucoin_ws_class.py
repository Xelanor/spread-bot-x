import asyncio
import websockets
import json
import traceback
from uuid import uuid4
import time

from exchanges.kucoin.kucoin_api_class import KucoinAPI


class KucoinWS:
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
            if "Depth" in message["topic"]:
                asks = message["data"]["asks"]
                bids = message["data"]["bids"]
                depth("Kucoin", asks, bids)
        except:
            print("Received message:", message)

    async def connect_public_websocket(self, depth=None):
        Kucoin = KucoinAPI(
            self.ticker, self.public_key, self.private_key, self.group, self.kyc
        )
        token, endpoint = Kucoin.create_ws_listen_key()
        ws_connect_id = str(uuid4()).replace("-", "")
        ws_endpoint = f"{endpoint}?token={token}&connectId={ws_connect_id}"

        params = json.dumps(
            {
                "id": str(int(time.time() * 1000)),
                "type": "subscribe",
                "topic": f"/spotMarket/level2Depth5:{self.tick}-USDT",
                "privateChannel": False,
                "response": True,
            }
        )
        try:
            async with websockets.connect(ws_endpoint) as websocket:
                await websocket.send(params)
                while True:
                    message = await websocket.recv()
                    await self.on_message(message, depth=depth)
        except (
            websockets.exceptions.ConnectionClosed,
            websockets.exceptions.InvalidHandshake,
        ):

            print("Kucoin Connection closed, restarting...")
            print(traceback.format_exc())
            await self.connect_public_websocket(depth=depth)

    async def fetch_account_balance(self, balance):
        Kucoin = KucoinAPI(
            self.ticker, self.public_key, self.private_key, self.group, self.kyc
        )

        while True:
            try:
                self.account_balance = Kucoin.get_account_balance()
                balance("Kucoin", self.kyc, self.account_balance)
                await asyncio.sleep(0.2)
            except:
                await asyncio.sleep(3)

    async def main(self, depth=None, balance=None):
        if depth:
            tasks = [
                self.connect_public_websocket(depth),
            ]

        if balance:
            tasks = [
                self.fetch_account_balance(balance),
            ]
        await asyncio.gather(*tasks)
