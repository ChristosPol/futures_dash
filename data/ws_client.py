# data/ws_client.py
import asyncio
import json
import threading
import time
import websockets

LATEST_DATA = {}
WS_RUNNING = False


def get_latest(symbol):
    """Return latest websocket data for a given futures product."""
    return LATEST_DATA.get(symbol, {})


async def _ws_loop():
    global WS_RUNNING

    url = "wss://futures.kraken.com/ws/v1"
    print("WebSocket: Connecting...")

    try:
        async with websockets.connect(url, ping_interval=None) as ws:

            # Subscribe to Kraken Futures Ticker
            await ws.send(json.dumps({
                "event": "subscribe",
                "feed": "ticker",
                "product_ids": ["PF_SOLUSD"]
            }))

            WS_RUNNING = True
            print("WebSocket: Connected.")

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                except asyncio.TimeoutError:
                    await ws.ping()
                    continue

                data = json.loads(msg)

                if "product_id" in data:
                    symbol = data["product_id"]
                    LATEST_DATA[symbol] = data

    except Exception as e:
        print(f"WebSocket error: {e}")
        WS_RUNNING = False
        time.sleep(3)
        asyncio.create_task(_ws_loop())  # reconnect


def start_ws_thread():
    """Run websocket listener in dedicated background thread."""
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_ws_loop())

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
