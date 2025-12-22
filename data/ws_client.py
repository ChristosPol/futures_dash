# data/ws_client.py
import asyncio
import json
import threading
import time
import websockets
from collections import deque

from data.metrics_engine import add_trade


# ============================================================
# GLOBAL STATE
# ============================================================

LATEST_DATA = {}
WS_RUNNING = False

# ---- Panel 3 buckets (permanent) ----
PRICE_BUCKETS = {}
BUCKET_SIZE = 0.50

LAST_BUCKET = None
LAST_PRICE = None
LAST_SIDE = None

# ---- Flash effect ----
FLASH_BUCKET = None
FLASH_STRENGTH = 1.0
FLASH_DECAY = 0.85

# ---- CVD, tape, velocity ----
CVD = 0.0
LAST_TRADES = []

TRADE_TIMESTAMPS = []
BUY_TIMESTAMPS = []
SELL_TIMESTAMPS = []

# ---- Panel 7: Micro-Momentum ----
PREV_TRADE_PRICE = None
PRICE_DISPLACEMENT = []      # (timestamp, ΔPrice)

# ------------------------------------------------------------
# PANEL 8 – REAL HOURLY PRICE MOVEMENT (OHLC)
# ------------------------------------------------------------
HOURLY_FLOW = {}   # hour_ts → { open, close, high, low, buy_vol, sell_vol }

def _get_hour_timestamp(ts):
    """Return timestamp rounded down to the start of the hour."""
    return int(ts // 3600 * 3600)


# ============================================================
# PANEL 1 - MULTI-COIN LIVE TRADES
# ============================================================
MULTI_COIN_TRADES = {
    "PF_XBTUSD": deque(maxlen=2000),
    "PF_ETHUSD": deque(maxlen=2000),
    "PF_SOLUSD": deque(maxlen=2000),
    "PF_ADAUSD": deque(maxlen=2000)
}

COIN_REFERENCE_PRICES = {}

TRADE_COUNTS = {
    "PF_XBTUSD": 0,
    "PF_ETHUSD": 0,
    "PF_SOLUSD": 0,
    "PF_ADAUSD": 0
}


# ============================================================
# PANEL 2 - ORDER BOOK DEPTH
# ============================================================
ORDER_BOOK = {
    "bids": [],  # [[price, volume], ...]
    "asks": []   # [[price, volume], ...]
}


def _update_multi_coin_trade(product_id, price, timestamp):
    """
    Store trade for multi-coin chart (Panel 1).
    Each coin stores: (timestamp, price)
    """
    if product_id not in MULTI_COIN_TRADES:
        return
    
    if product_id not in COIN_REFERENCE_PRICES:
        COIN_REFERENCE_PRICES[product_id] = price
        print(f"✓ Set reference price for {product_id}: ${price:.2f}")
    
    MULTI_COIN_TRADES[product_id].append((timestamp, price))
    TRADE_COUNTS[product_id] += 1
    
    if TRADE_COUNTS[product_id] % 100 == 0:
        print(f"📊 {product_id}: {TRADE_COUNTS[product_id]} trades, last price ${price:.2f}")


# ============================================================
# HELPERS
# ============================================================

def get_latest(symbol):
    return LATEST_DATA.get(symbol, {})


def _bucket_from_price(price: float) -> float:
    return round(price / BUCKET_SIZE) * BUCKET_SIZE


def _update_price_bucket(price: float, volume: float, side: str):
    """
    Updates:
    - Buckets
    - Flash effect
    - CVD
    - Tape
    - Velocity
    - Micro-momentum
    - REAL HOURLY PRICE MOVEMENT (Panel 8)
    """
    global LAST_BUCKET, LAST_PRICE, LAST_SIDE
    global FLASH_BUCKET, FLASH_STRENGTH
    global CVD, LAST_TRADES
    global PREV_TRADE_PRICE, PRICE_DISPLACEMENT
    global TRADE_TIMESTAMPS, BUY_TIMESTAMPS, SELL_TIMESTAMPS
    global HOURLY_FLOW

    ts_now = time.time()
    hour_ts = _get_hour_timestamp(ts_now)

    # ============================================
    #   1) HOURLY PRICE ENGINE (REAL MOVEMENT)
    # ============================================
    if hour_ts not in HOURLY_FLOW:
        HOURLY_FLOW[hour_ts] = {
            "open": price,
            "close": price,
            "high": price,
            "low": price,
            "buy_vol": 0.0,
            "sell_vol": 0.0
        }

    h = HOURLY_FLOW[hour_ts]
    h["close"] = price
    h["high"] = max(h["high"], price)
    h["low"] = min(h["low"], price)

    if side == "buy":
        h["buy_vol"] += volume
    else:
        h["sell_vol"] += volume

    # keep last 24 hours
    if len(HOURLY_FLOW) > 48:
        oldest = sorted(HOURLY_FLOW.keys())[:-24]
        for k in oldest:
            HOURLY_FLOW.pop(k, None)

    # ============================================
    #   2) PANEL 3 + CVD + MOMENTUM
    # ============================================

    bucket = _bucket_from_price(price)

    if bucket not in PRICE_BUCKETS:
        PRICE_BUCKETS[bucket] = {"buy": 0.0, "sell": 0.0}

    if side not in ("buy", "sell"):
        side = "buy"

    PRICE_BUCKETS[bucket][side] += volume

    LAST_BUCKET = bucket
    LAST_PRICE = price
    LAST_SIDE = side

    FLASH_BUCKET = bucket
    FLASH_STRENGTH = 1.0

    CVD += volume if side == "buy" else -volume

    LAST_TRADES.append({
        "price": price,
        "volume": volume,
        "side": side,
        "time": ts_now
    })
    LAST_TRADES[:] = LAST_TRADES[-20:]

    TRADE_TIMESTAMPS.append(ts_now)
    if side == "buy":
        BUY_TIMESTAMPS.append((ts_now, volume))
    else:
        SELL_TIMESTAMPS.append((ts_now, volume))

    # Micro-momentum
    if PREV_TRADE_PRICE is not None:
        PRICE_DISPLACEMENT.append((ts_now, price - PREV_TRADE_PRICE))
        PRICE_DISPLACEMENT[:] = PRICE_DISPLACEMENT[-300:]

    PREV_TRADE_PRICE = price


def _decay_flash():
    global FLASH_STRENGTH, FLASH_BUCKET
    if FLASH_BUCKET is not None:
        FLASH_STRENGTH *= FLASH_DECAY
        if FLASH_STRENGTH < 0.05:
            FLASH_BUCKET = None


# ============================================================
# WEBSOCKET LOOP
# ============================================================

async def _ws_loop():
    global WS_RUNNING, ORDER_BOOK

    url = "wss://futures.kraken.com/ws/v1"
    products = ["PF_XBTUSD", "PF_ETHUSD", "PF_SOLUSD", "PF_ADAUSD"]

    while True:
        print(f"WebSocket: Connecting to {products}...")

        try:
            async with websockets.connect(url, ping_interval=None) as ws:

                # Subscribe to ticker
                await ws.send(json.dumps({
                    "event": "subscribe",
                    "feed": "ticker",
                    "product_ids": products
                }))

                # Subscribe to trades
                await ws.send(json.dumps({
                    "event": "subscribe",
                    "feed": "trade",
                    "product_ids": products
                }))

                # Subscribe to order book (for PF_SOLUSD)
                await ws.send(json.dumps({
                    "event": "subscribe",
                    "feed": "book",
                    "product_ids": ["PF_SOLUSD"]
                }))

                WS_RUNNING = True
                print("WebSocket: Connected and subscribed to all products.")

                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    except asyncio.TimeoutError:
                        await ws.ping()
                        continue

                    data = json.loads(msg)

                    # Debug: Print subscription confirmations
                    if data.get("event") == "subscribed":
                        print(f"✓ Subscribed to {data.get('feed')} for {data.get('product_ids')}")
                        continue

                    if data.get("feed") == "ticker":
                        if "product_id" in data:
                            LATEST_DATA[data["product_id"]] = data
                        _decay_flash()
                        continue

                    # ===== ORDER BOOK UPDATES =====
                    if data.get("feed") == "book_snapshot":
                        # Full order book snapshot
                        if data.get("product_id") == "PF_SOLUSD":
                            try:
                                bids_data = data.get("bids", [])
                                asks_data = data.get("asks", [])
                                
                                ORDER_BOOK["bids"] = [[float(b["price"]), float(b["qty"])] for b in bids_data]
                                ORDER_BOOK["asks"] = [[float(a["price"]), float(a["qty"])] for a in asks_data]
                                print(f"📖 Order book snapshot received: {len(ORDER_BOOK['bids'])} bids, {len(ORDER_BOOK['asks'])} asks")
                            except Exception as e:
                                print(f"Error parsing book snapshot: {e}, data: {data}")
                        continue

                    if data.get("feed") == "book":
                        # Incremental order book update (ONE LEVEL AT A TIME)
                        if data.get("product_id") == "PF_SOLUSD":
                            try:
                                side = data.get("side")  # "buy" or "sell"
                                price = float(data.get("price"))
                                qty = float(data.get("qty"))
                                
                                if side == "buy":
                                    # Update bids
                                    ORDER_BOOK["bids"] = [b for b in ORDER_BOOK["bids"] if b[0] != price]
                                    if qty > 0:
                                        ORDER_BOOK["bids"].append([price, qty])
                                    # Keep sorted (highest first)
                                    ORDER_BOOK["bids"].sort(key=lambda x: x[0], reverse=True)
                                    ORDER_BOOK["bids"] = ORDER_BOOK["bids"][:100]
                                    
                                elif side == "sell":
                                    # Update asks
                                    ORDER_BOOK["asks"] = [a for a in ORDER_BOOK["asks"] if a[0] != price]
                                    if qty > 0:
                                        ORDER_BOOK["asks"].append([price, qty])
                                    # Keep sorted (lowest first)
                                    ORDER_BOOK["asks"].sort(key=lambda x: x[0])
                                    ORDER_BOOK["asks"] = ORDER_BOOK["asks"][:100]

                            except Exception as e:
                                print(f"Error parsing book update: {e}, data: {data}")

                        continue

                    if data.get("feed") == "trade":
                        product_id = data.get("product_id")

                        if "price" in data and "qty" in data:
                            try:
                                price = float(data["price"])
                                volume = float(data["qty"])
                                side = data.get("side", "buy")
                                ts_ms = data.get("time")
                                ts = ts_ms / 1000 if ts_ms else time.time()

                                _update_multi_coin_trade(product_id, price, ts)

                                if product_id == "PF_SOLUSD":
                                    add_trade(price, volume, side, ts)
                                    _update_price_bucket(price, volume, side)

                            except Exception as e:
                                print(f"Trade parse error for {product_id}:", e)
                            _decay_flash()
                            continue

                        if "trades" in data:
                            for t in data["trades"]:
                                try:
                                    price = float(t["price"])
                                    volume = float(t["qty"])
                                    side = t.get("side", "buy")
                                    ts = t.get("timestamp", time.time())

                                    _update_multi_coin_trade(product_id, price, ts)

                                    if product_id == "PF_SOLUSD":
                                        add_trade(price, volume, side, ts)
                                        _update_price_bucket(price, volume, side)
                                except:
                                    pass
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
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_ws_loop())

    thread = threading.Thread(target=run, daemon=True)
    thread.start()