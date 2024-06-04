import asyncio
import websockets
import json
import traceback
from uuid import uuid4
import time
import gzip
import io

from exchanges.bingx.utils import WS_HOST

from exchanges.bingx.bingx_api_class import BingXAPI


class BingXWS:
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
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode="rb")
        decompressed_data = compressed_data.read()
        message = decompressed_data.decode("utf-8")
        message = json.loads(message)
        try:
            if "data" in message and "asks" in message["data"]:
                asks = message["data"]["asks"][::-1]
                bids = message["data"]["bids"]
                depth("BingX", asks, bids)
        except:
            print("Received message:", message)

    async def connect_public_websocket(self, depth=None):
        ws_connect_id = str(uuid4()).replace("-", "")
        params = json.dumps(
            {
                "id": ws_connect_id,
                "reqType": "sub",
                "dataType": f"{self.tick}-USDT@depth10",
            }
        )
        try:
            async with websockets.connect(WS_HOST) as websocket:
                await websocket.send(params)
                while True:
                    message = await websocket.recv()
                    await self.on_message(message, depth=depth)
        except (
            websockets.exceptions.ConnectionClosed,
            websockets.exceptions.InvalidHandshake,
        ):

            print("BingX Connection closed, restarting...")
            print(traceback.format_exc())
            await self.connect_public_websocket(depth=depth)

    async def connect_private_websocket(self, listenKey, balance=None):
        ws_connect_id = str(uuid4()).replace("-", "")
        params = json.dumps(
            {
                "id": ws_connect_id,
                "reqType": "sub",
                "dataType": "ACCOUNT_UPDATE",
            }
        )
        try:
            async with websockets.connect(
                WS_HOST + f"?listenKey={listenKey}"
            ) as websocket:
                await websocket.send(params)
                while True:
                    message = await websocket.recv()
                    await self.on_message(message, balance=balance)
        except (
            websockets.exceptions.ConnectionClosed,
            websockets.exceptions.InvalidHandshake,
        ):

            print("BingX Connection closed, restarting...")
            print(traceback.format_exc())
            await self.connect_private_websocket(balance=balance)

    async def fetch_account_balance(self, balance):
        BingX = BingXAPI(
            self.ticker, self.public_key, self.private_key, self.group, self.kyc
        )

        while True:
            try:
                self.account_balance = BingX.get_account_balance()
                balance("BingX", self.kyc, self.account_balance)
                await asyncio.sleep(0.5)
            except:
                await asyncio.sleep(3)

    async def main(self, depth=None, balance=None):
        if depth:
            tasks = [
                self.connect_public_websocket(depth),
            ]

        # if balance:
        #     BingX = BingXAPI(self.ticker, self.public_key, self.private_key, self.group)
        #     listenKey = BingX.create_ws_listen_key()
        #     self.account_balance = BingX.get_account_balance()

        #     tasks = [
        #         self.connect_private_websocket(listenKey, balance),
        #     ]

        if balance:
            tasks = [
                self.fetch_account_balance(balance),
            ]
        await asyncio.gather(*tasks)
