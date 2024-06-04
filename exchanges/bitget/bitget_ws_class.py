import asyncio
import websockets
import json
import traceback

from .utils import WS_HOST
from .bitget_api_class import BitgetAPI


class BitgetWS:
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
        self.keep_alive_interval = 25  # Interval for sending ping messages
        self.keep_alive_timeout = 30  # Timeout for receiving pong responses

    async def on_message(self, message, depth=None, balance=None):
        if message == "pong":
            self.last_pong_received = asyncio.get_event_loop().time()

        else:
            message = json.loads(message)
            try:
                if "data" in message:
                    asks = message["data"][0]["asks"]
                    bids = message["data"][0]["bids"]
                    depth("Bitget", asks, bids)
            except:
                print("Received message:", message)

    async def send_keep_alive(self, websocket):
        while True:
            try:
                await websocket.send("ping")  # Send ping message
                await asyncio.sleep(self.keep_alive_interval)  # Wait for the interval
                if (
                    self.last_pong_received is None
                    or (asyncio.get_event_loop().time() - self.last_pong_received)
                    > self.keep_alive_timeout
                ):
                    print("Pong response not received within timeout")
                    raise ValueError("Pong response not received within timeout")
            except Exception as e:
                print(f"Error sending ping: {e}")
                break

    async def connect_public_websocket(self, depth=None):
        params = json.dumps(
            {
                "op": "subscribe",
                "args": [
                    {
                        "instType": "SPOT",
                        "channel": "books5",
                        "instId": f"{self.tick}USDT",
                    }
                ],
            }
        )
        try:
            async with websockets.connect(WS_HOST) as websocket:
                await websocket.send(params)

                keep_alive_task = asyncio.create_task(self.send_keep_alive(websocket))

                while True:
                    message = await websocket.recv()
                    await self.on_message(message, depth=depth)
        except (
            websockets.exceptions.ConnectionClosed,
            websockets.exceptions.InvalidHandshake,
            Exception,
        ) as e:
            print("Bitget Connection closed, restarting...")
            # print(traceback.format_exc())
            await self.connect_public_websocket(depth=depth)

    async def fetch_account_balance(self, balance):
        Bitget = BitgetAPI(
            self.ticker, self.public_key, self.private_key, self.group, self.kyc
        )

        while True:
            try:
                self.account_balance = Bitget.get_account_balance()
                balance("Bitget", self.kyc, self.account_balance)
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
