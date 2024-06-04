import asyncio
import websockets
import json
import zlib
import traceback

from exchanges.bitmart.utils import WS_HOST, WS_LOGIN_HOST, sign, utc_timestamp
from exchanges.bitmart.bitmart_api_class import BitmartAPI


class BitmartWS:
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

    def inflate(self, data):
        decompress = zlib.decompressobj(-zlib.MAX_WBITS)
        inflated = decompress.decompress(data)
        inflated += decompress.flush()
        return inflated.decode("UTF-8")

    def convert(self, message):
        if type(message) == bytes:
            return self.inflate(message)
        else:
            return message

    async def on_message(self, message, depth=None, balance=None):
        message = json.loads(self.convert(message))
        if depth and "table" in message and message["table"] == "spot/depth5":
            asks = message["data"][0]["asks"]
            bids = message["data"][0]["bids"]
            depth("Bitmart", asks, bids)
        else:
            print("Received message:", message)

    async def authorize(self, message):
        message = json.loads(message)
        if message["event"] == "login":
            return True
        return False

    async def connect_public_websocket(self, depth=None):
        params = json.dumps(
            {"op": "subscribe", "args": [f"spot/depth5:{self.tick}_USDT"]}
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

            print("Bitmart Connection closed, restarting...")
            print(traceback.format_exc())
            await self.connect_public_websocket(depth=depth)

    async def connect_private_websocket(self, balance=None):
        ts = utc_timestamp()
        substring = f"{str(ts)}#{self.group}#bitmart.WebSocket"
        signature = sign(self.private_key, substring)
        login_params = json.dumps(
            {"op": "login", "args": [self.public_key, ts, signature]}
        )
        params = json.dumps(
            {"op": "subscribe", "args": ["spot/user/balance:BALANCE_UPDATE"]}
        )

        async with websockets.connect(WS_LOGIN_HOST) as websocket:
            await websocket.send(login_params)
            message = await websocket.recv()
            print(f"[websockets] Recv:{message}")
            result = await self.authorize(message)
            if result:
                print("OK lets go")
                await websocket.send(params)

            while True:
                message = await websocket.recv()
                await self.on_message(message, balance=balance)

    async def fetch_account_balance(self, balance):
        Bitmart = BitmartAPI(
            self.ticker, self.public_key, self.private_key, self.group, self.kyc
        )

        while True:
            try:
                self.account_balance = Bitmart.get_account_balance()
                balance("Bitmart", self.kyc, self.account_balance)
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
