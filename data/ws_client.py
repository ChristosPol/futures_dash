# data/ws_client.py
import asyncio
import json
import threading
import time
import websockets

from data.metrics_engine import add_trade

LATEST_DATA = {}
WS_RUNNING = False


def get_latest(symbol):
    return LATEST_DATA.get(symbol, {})


async def _ws_loop():
    global WS_RUNNING

    url = "wss://futures.kraken.com/ws/v1"
    print("WebSocket: Connecting...")

    try:
        async with websockets.connect(url, ping_interval=None) as ws:

            # Subscribe to PERPETUAL SOL/USD
            await ws.send(json.dumps({
                "event": "subscribe",
                "feed": "ticker",
                "product_ids": ["PF_SOLUSD"]
            }))

            await ws.send(json.dumps({
                "event": "subscribe",
                "feed": "trade",
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

                # -------- TICKER feed ----------
                if data.get("feed") == "ticker" and "product_id" in data:
                    LATEST_DATA[data["product_id"]] = data
                    continue

                # -------- TRADE feed ----------
                if data.get("feed") == "trade":

                    # FUTURES FORMAT: single trade
                    if "qty" in data and "price" in data:
                        try:
                            price = float(data["price"])
                            volume = float(data["qty"])
                            side = data.get("side", "buy")     # default if missing
                            ts_ms = data.get("time")          # milliseconds
                            ts = ts_ms / 1000 if ts_ms else time.time()

                            add_trade(price, volume, side, ts)

                        except Exception as e:
                            print("Trade parse error:", e)

                        continue

                    # SPOT FORMAT (not used but included for safety)
                    if "trades" in data:
                        for t in data["trades"]:
                            try:
                                price = float(t["price"])
                                volume = float(t["qty"])
                                side = t.get("side", "buy")
                                ts = t["timestamp"]
                                add_trade(price, volume, side, ts)
                            except Exception as e:
                                print("Trade parse error:", e)
                        continue

    except Exception as e:
        print("WebSocket error:", e)
        WS_RUNNING = False
        time.sleep(3)
        asyncio.create_task(_ws_loop())


def start_ws_thread():
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_ws_loop())

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
