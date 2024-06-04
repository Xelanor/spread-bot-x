import asyncio
import websockets
import json
import traceback
from uuid import uuid4
import gzip
import io

from .utils import WS_HOST
from .bybit_api_class import BybitAPI


class BybitWS:
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

    def find_index(self, source, target, key):
        """
        Find the index in source list of the targeted ID.
        """
        return next(i for i, j in enumerate(source) if j[key] == target[key])

    def _process_delta_orderbook(self, message, topic):
        if "snapshot" in message["type"]:
            self.data = message["data"]
            return

        book_sides = {"b": message["data"]["b"], "a": message["data"]["a"]}
        # Make updates according to delta response.
        for side, entries in book_sides.items():
            for entry in entries:
                # Delete.
                if float(entry[1]) == 0:
                    index = self.find_index(self.data[side], entry, 0)
                    self.data[side].pop(index)
                    continue

                # Insert.
                price_level_exists = entry[0] in [level[0] for level in self.data[side]]
                if not price_level_exists:
                    self.data[side].append(entry)
                    continue

                # Update.
                qty_changed = entry[1] != next(
                    level[1] for level in self.data[side] if level[0] == entry[0]
                )
                if price_level_exists and qty_changed:
                    index = self.find_index(self.data[side], entry, 0)
                    self.data[side][index] = entry
                    continue

    async def on_message(self, message, depth=None, balance=None):
        message = json.loads(message)
        try:
            topic = message["topic"]
            if "orderbook" in topic:
                self._process_delta_orderbook(message, topic)
                depth("Bybit", self.data["a"], self.data["b"])
        except:
            print("Received message:", message)

    async def connect_public_websocket(self, depth=None):
        params = json.dumps(
            {"op": "subscribe", "args": [f"orderbook.50.{self.tick}USDT"]}
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

            print("Bybit Connection closed, restarting...")
            print(traceback.format_exc())
            await self.connect_public_websocket(depth=depth)

    async def fetch_account_balance(self, balance):
        Bybit = BybitAPI(
            self.ticker, self.public_key, self.private_key, self.group, self.kyc
        )

        while True:
            try:
                self.account_balance = Bybit.get_account_balance()
                balance("Bybit", self.kyc, self.account_balance)
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
