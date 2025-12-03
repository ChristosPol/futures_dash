# data/ws_client.py
import asyncio
import json
import threading
import time
import websockets

from data.metrics_engine import add_trade

# ============================================================
# GLOBAL STATE
# ============================================================

LATEST_DATA = {}           # latest ticker snapshot
WS_RUNNING = False

# ---- Panel 3 bucket engine ----
PRICE_BUCKETS = {}         # { bucket_price : { "buy": vol, "sell": vol } }
BUCKET_SIZE = 0.50         # bucket step

LAST_BUCKET = None         # last bucket that received a trade
LAST_PRICE = None          # last trade price

# ---- Flash Pulse Effect ----
FLASH_BUCKET = None
FLASH_STRENGTH = 1.0
FLASH_DECAY = 0.85         # neon fade speed

# ---- Panels 4,5,6 ----
CVD = 0.0                  # cumulative delta
LAST_TRADES = []           # store last 10 trades
TRADE_TIMESTAMPS = []      # for velocity


def get_latest(symbol):
    return LATEST_DATA.get(symbol, {})


# ============================================================
# HELPERS
# ============================================================

def _bucket_from_price(price: float) -> float:
    """Compute 0.50 bucket from price."""
    return round(price / BUCKET_SIZE) * BUCKET_SIZE


def _update_price_bucket(price: float, volume: float, side: str):
    """
    Update bucket volumes & last trade state.
    Trigger flash pulse. Update tape + CVD + timestamps.
    """
    global LAST_BUCKET, LAST_PRICE
    global FLASH_BUCKET, FLASH_STRENGTH
    global CVD, LAST_TRADES, TRADE_TIMESTAMPS

    bucket = _bucket_from_price(price)

    if bucket not in PRICE_BUCKETS:
        PRICE_BUCKETS[bucket] = {"buy": 0.0, "sell": 0.0}

    if side not in ("buy", "sell"):
        side = "buy"

    PRICE_BUCKETS[bucket][side] += volume

    # ---- Last trade ----
    LAST_BUCKET = bucket
    LAST_PRICE = price

    # ---- Flash pulse trigger ----
    FLASH_BUCKET = bucket
    FLASH_STRENGTH = 1.0

    # ---- CVD update ----
    delta = volume if side == "buy" else -volume
    CVD += delta

    # ---- Last 10 trades storage ----
    trade_record = {
        "price": price,
        "volume": volume,
        "side": side,
        "time": time.time()
    }
    LAST_TRADES.append(trade_record)
    LAST_TRADES = LAST_TRADES[-10:]  # keep only last 10

    # ---- For velocity ----
    TRADE_TIMESTAMPS.append(time.time())


def _decay_flash():
    """Decay flash over time."""
    global FLASH_STRENGTH, FLASH_BUCKET

    if FLASH_BUCKET is not None:
        FLASH_STRENGTH *= FLASH_DECAY
        if FLASH_STRENGTH < 0.05:
            FLASH_BUCKET = None


# ============================================================
# MAIN ASYNC WEBSOCKET LOOP
# ============================================================

async def _ws_loop():
    global WS_RUNNING

    url = "wss://futures.kraken.com/ws/v1"
    print("WebSocket: Connecting...")

    try:
        async with websockets.connect(url, ping_interval=None) as ws:

            # Subscribe to PF_SOLUSD ticker + trades
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

                # ---- Ticker feed ----
                if data.get("feed") == "ticker" and "product_id" in data:
                    LATEST_DATA[data["product_id"]] = data
                    _decay_flash()
                    continue

                # ---- Trade feed ----
                if data.get("feed") == "trade":

                    # FUTURES single-trade format
                    if "qty" in data and "price" in data:
                        try:
                            price = float(data["price"])
                            volume = float(data["qty"])
                            side = data.get("side", "buy")
                            ts_ms = data.get("time")
                            ts = ts_ms / 1000 if ts_ms else time.time()

                            add_trade(price, volume, side, ts)
                            _update_price_bucket(price, volume, side)
                            _decay_flash()

                        except Exception as e:
                            print("Trade parse error:", e)

                        continue

                    # SPOT multi-trade fallback
                    if "trades" in data:
                        for t in data["trades"]:
                            try:
                                price = float(t["price"])
                                volume = float(t["qty"])
                                side = t.get("side", "buy")
                                ts = t.get("timestamp", time.time())

                                add_trade(price, volume, side, ts)
                                _update_price_bucket(price, volume, side)
                                _decay_flash()

                            except Exception as e:
                                print("Trade parse error:", e)
                        continue

    except Exception as e:
        print("WebSocket error:", e)
        WS_RUNNING = False
        time.sleep(3)
        return await _ws_loop()


# ============================================================
# THREAD STARTER
# ============================================================

def start_ws_thread():
    """Run WebSocket loop in its own thread."""
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_ws_loop())

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
