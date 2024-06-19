import asyncio
import websockets
import json
import traceback
from uuid import uuid4
import time
import gzip
import io

from .utils import WS_HOST
from .htx_api_class import HtxAPI


class HtxWS:
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

    async def on_message(self, message, websocket, depth=None, balance=None):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode="rb")
        decompressed_data = compressed_data.read()
        message = decompressed_data.decode("utf-8")
        message = json.loads(message)
        try:
            if "tick" in message:
                asks = message["tick"]["asks"]
                bids = message["tick"]["bids"]
                depth("Htx", asks, bids)
            if "ping" in message:
                pong = {"pong": message["ping"]}
                await websocket.send(json.dumps(pong))
        except:
            print("Received message:", message)

    async def connect_public_websocket(self, depth=None):
        ws_connect_id = str(uuid4()).replace("-", "")
        params = json.dumps(
            {
                "sub": f"market.{self.tick.lower()}usdt.depth.step0",
                "id": ws_connect_id,
            }
        )
        try:
            async with websockets.connect(WS_HOST) as websocket:
                await websocket.send(params)
                while True:
                    message = await websocket.recv()
                    await self.on_message(message, websocket, depth=depth)
        except (
            websockets.exceptions.ConnectionClosed,
            websockets.exceptions.InvalidHandshake,
        ):

            print("Htx Connection closed, restarting...")
            await self.connect_public_websocket(depth=depth)

    async def fetch_account_balance(self, balance):
        Htx = HtxAPI(
            self.ticker, self.public_key, self.private_key, self.group, self.kyc
        )

        while True:
            try:
                self.account_balance = Htx.get_account_balance()
                balance("Htx", self.kyc, self.account_balance)
                await asyncio.sleep(0.5)
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


# api = HtxWS(
#     "BTC/USDT",
#     "cf5994d9-da9d62a1-bvrge3rf7j-b4d71",
#     "5381db71-945fbbfb-68068d79-5f878",
#     "maker",
#     "kyc",
# )
# asyncio.run(api.main(depth=1))
