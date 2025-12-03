# data/ws_client.py
import asyncio
import json
import threading
import time
import websockets

from data.metrics_engine import add_trade

# ---------------- GLOBAL STATE ----------------

LATEST_DATA = {}     # latest ticker snapshot
WS_RUNNING = False

# For Panel 3 (price buckets)
PRICE_BUCKETS = {}   # {bucket_price: {"buy": vol, "sell": vol}}
BUCKET_SIZE = 0.50   # USD bucket size

LAST_BUCKET = None   # bucket where the last trade landed
LAST_PRICE = None    # last trade price


def get_latest(symbol):
    return LATEST_DATA.get(symbol, {})


# ---------------- HELPERS ----------------

def _bucket_from_price(price: float) -> float:
    """
    Compute the BUCKET_SIZE price bucket for a given price.
    """
    return round(price / BUCKET_SIZE) * BUCKET_SIZE


def _update_price_bucket(price: float, volume: float, side: str):
    """
    Update real-time volume aggregation per price bucket and
    track the last trade's bucket and price.
    """
    global LAST_BUCKET, LAST_PRICE

    bucket = _bucket_from_price(price)

    if bucket not in PRICE_BUCKETS:
        PRICE_BUCKETS[bucket] = {"buy": 0.0, "sell": 0.0}

    if side not in ("buy", "sell"):
        side = "buy"

    PRICE_BUCKETS[bucket][side] += volume

    LAST_BUCKET = bucket
    LAST_PRICE = price


# ---------------- MAIN WS LOOP ----------------

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

                            # Update hourly metrics (Panel 2)
                            add_trade(price, volume, side, ts)

                            # Update price buckets + last trade info (Panel 3)
                            _update_price_bucket(price, volume, side)

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
                                _update_price_bucket(price, volume, side)

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
