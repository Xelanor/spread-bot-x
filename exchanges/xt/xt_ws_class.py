import asyncio
import websockets
import json
import traceback
from uuid import uuid4

from .utils import WS_HOST
from .xt_api_class import XtAPI


class XtWS:
    def __init__(
        self, ticker=None, public_key=None, private_key=None, group=None, kyc=None
    ):
        self.ticker = ticker
        if ticker:
            self.tick = ticker.split("/")[0].lower()
        self.public_key = public_key
        self.private_key = private_key
        self.group = group
        self.kyc = kyc
        self.keep_alive_interval = 50  # Interval for sending ping messages
        self.keep_alive_timeout = 55  # Timeout for receiving pong responses

    async def on_message(self, message, depth=None, balance=None):
        if message == "pong":
            self.last_pong_received = asyncio.get_event_loop().time()

        else:
            message = json.loads(message)
            try:
                if "data" in message:
                    asks = message["data"]["a"]
                    bids = message["data"]["b"]
                    depth("XT", asks, bids)
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
        ws_connect_id = str(uuid4()).replace("-", "")
        params = json.dumps(
            {
                "method": "subscribe",
                "params": [f"depth@{self.tick}_usdt,5"],
                "id": ws_connect_id,
            }
        )
        print(params)
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
            print("XT Connection closed, restarting...")
            # print(traceback.format_exc())
            await self.connect_public_websocket(depth=depth)

    async def fetch_account_balance(self, balance):
        Xt = XtAPI(self.ticker, self.public_key, self.private_key, self.group, self.kyc)

        while True:
            try:
                self.account_balance = Xt.get_account_balance()
                balance("XT", self.kyc, self.account_balance)
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


# api = XtWS(
#     "BTC/USDT",
#     "a862725b-f10b-4d09-966f-b844686d65f3",
#     "5395d6b8473cf99137b95b78ce9804d1302fa3fd",
#     "maker",
#     "Berke",
# )
# asyncio.run(api.main(depth=1))
