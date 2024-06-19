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

        self.orderbooks = {"b": [], "a": []}

    def _process_delta_orderbook(self, message, topic):
        data = message.get("data", {})

        # Check if it's a snapshot
        if "type" in message and message["type"] == "snapshot":
            self._reset_orderbook(data)
        else:
            self._apply_delta(data)

    def _reset_orderbook(self, data):
        self.orderbooks["b"] = sorted(
            [[price, size] for price, size in data.get("b", [])],
            key=lambda x: float(x[0]),
            reverse=True,
        )
        self.orderbooks["a"] = sorted(
            [[price, size] for price, size in data.get("a", [])],
            key=lambda x: float(x[0]),
        )

    def _apply_delta(self, data):
        for side in ["b", "a"]:
            updates = {float(price): float(size) for price, size in data.get(side, [])}
            book = {float(price): float(size) for price, size in self.orderbooks[side]}

            for price, size in updates.items():
                if size == 0:
                    if price in book:
                        del book[price]
                else:
                    book[price] = size

            sorted_book = sorted(
                book.items(), key=lambda x: x[0], reverse=(side == "b")
            )
            self.orderbooks[side] = [[price, size] for price, size in sorted_book]

    async def on_message(self, message, depth=None, balance=None):
        message = json.loads(message)
        try:
            topic = message["topic"]
            if "orderbook" in topic:
                self._process_delta_orderbook(message, topic)
                depth("Bybit", self.orderbooks["a"], self.orderbooks["b"])
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
