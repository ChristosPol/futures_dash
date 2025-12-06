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
BUCKET_SIZE = 0.50

LAST_BUCKET = None         # last bucket that received a trade
LAST_PRICE = None          # last trade price
LAST_SIDE = None           # side of last trade

# ---- Flash Pulse Effect ----
FLASH_BUCKET = None
FLASH_STRENGTH = 1.0
FLASH_DECAY = 0.85

# ---- Panels 4,5,6 ----
CVD = 0.0
LAST_TRADES = []                # last 10 trades

# Velocity tracking
TRADE_TIMESTAMPS = []           # for TPS
BUY_TIMESTAMPS = []             # (timestamp, volume)
SELL_TIMESTAMPS = []            # (timestamp, volume)

# ---- Panel 7: Micro-momentum tracking ----
PREV_TRADE_PRICE = None
PRICE_DISPLACEMENT = []         # list of (timestamp, ΔPrice)


# ============================================================
# HELPERS
# ============================================================

def get_latest(symbol):
    return LATEST_DATA.get(symbol, {})


def _bucket_from_price(price: float) -> float:
    """Compute bucket rounded to BUCKET_SIZE (default 0.50)."""
    return round(price / BUCKET_SIZE) * BUCKET_SIZE


def _update_price_bucket(price: float, volume: float, side: str):
    """
    Update all internal engines:
    - Bucket volume
    - Last trade info
    - Flash pulse
    - CVD
    - Last trades tape
    - Volume velocity
    - Micro-momentum (ΔPrice per trade)
    """
    global LAST_BUCKET, LAST_PRICE, LAST_SIDE
    global FLASH_BUCKET, FLASH_STRENGTH
    global CVD, LAST_TRADES
    global TRADE_TIMESTAMPS, BUY_TIMESTAMPS, SELL_TIMESTAMPS
    global PREV_TRADE_PRICE, PRICE_DISPLACEMENT

    bucket = _bucket_from_price(price)

    # Create bucket if missing
    if bucket not in PRICE_BUCKETS:
        PRICE_BUCKETS[bucket] = {"buy": 0.0, "sell": 0.0}

    if side not in ("buy", "sell"):
        side = "buy"

    PRICE_BUCKETS[bucket][side] += volume

    # Store last-trade attributes
    LAST_BUCKET = bucket
    LAST_PRICE = price
    LAST_SIDE = side

    # Flash pulse activate
    FLASH_BUCKET = bucket
    FLASH_STRENGTH = 1.0

    # ------------------------
    # CVD update
    # ------------------------
    delta = volume if side == "buy" else -volume
    CVD += delta

    # ------------------------
    # Last 10 trades storage
    # ------------------------
    ts_now = time.time()
    LAST_TRADES.append({
        "price": price,
        "volume": volume,
        "side": side,
        "time": ts_now
    })
    LAST_TRADES[:] = LAST_TRADES[-10:]

    # ------------------------
    # Velocity tracking
    # ------------------------
    TRADE_TIMESTAMPS.append(ts_now)

    if side == "buy":
        BUY_TIMESTAMPS.append((ts_now, volume))
    else:
        SELL_TIMESTAMPS.append((ts_now, volume))

    # ------------------------
    # Panel 7: Micro-momentum (ΔPrice per trade)
    # ------------------------
    if PREV_TRADE_PRICE is not None:
        displacement = price - PREV_TRADE_PRICE
        PRICE_DISPLACEMENT.append((ts_now, displacement))
        PRICE_DISPLACEMENT[:] = PRICE_DISPLACEMENT[-300:]  # keep last ~300 trades

    PREV_TRADE_PRICE = price


def _decay_flash():
    """Fade out the neon pulse highlight."""
    global FLASH_STRENGTH, FLASH_BUCKET

    if FLASH_BUCKET is not None:
        FLASH_STRENGTH *= FLASH_DECAY
        if FLASH_STRENGTH < 0.05:
            FLASH_BUCKET = None


# ============================================================
# MAIN WEBSOCKET LOOP (STABLE RECONNECTING VERSION)
# ============================================================

async def _ws_loop():
    global WS_RUNNING

    url = "wss://futures.kraken.com/ws/v1"

    while True:
        print("WebSocket: Connecting...")

        try:
            async with websockets.connect(url, ping_interval=None) as ws:

                # Subscribe to feeds
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

                # ---- MESSAGE LOOP ----
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    except asyncio.TimeoutError:
                        await ws.ping()
                        continue

                    data = json.loads(msg)

                    # ---- Ticker ----
                    if data.get("feed") == "ticker" and "product_id" in data:
                        LATEST_DATA[data["product_id"]] = data
                        _decay_flash()
                        continue

                    # ---- Trades ----
                    if data.get("feed") == "trade":

                        # Futures format
                        if "price" in data and "qty" in data:
                            try:
                                price = float(data["price"])
                                volume = float(data["qty"])
                                side = data.get("side", "buy")

                                ts_ms = data.get("time")
                                ts = ts_ms / 1000 if ts_ms else time.time()

                                add_trade(price, volume, side, ts)
                                _update_price_bucket(price, volume, side)

                            except Exception as e:
                                print("Trade parse error:", e)

                            _decay_flash()
                            continue

                        # Spot fallback (rare)
                        if "trades" in data:
                            for t in data["trades"]:
                                try:
                                    price = float(t["price"])
                                    volume = float(t["qty"])
                                    side = t.get("side", "buy")
                                    ts = t.get("timestamp", time.time())

                                    add_trade(price, volume, side, ts)
                                    _update_price_bucket(price, volume, side)

                                except Exception as e:
                                    print("Trade parse error:", e)

                            _decay_flash()
                            continue

        except Exception as e:
            print("WEBSOCKET ERROR:", e)
            WS_RUNNING = False

        print("Reconnecting in 2 seconds...")
        await asyncio.sleep(2)


# ============================================================
# THREAD STARTER
# ============================================================

def start_ws_thread():
    """Launch WebSocket loop in a background thread."""
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_ws_loop())

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
