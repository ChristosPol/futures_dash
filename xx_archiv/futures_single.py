import json
import websocket
from sty import fg, bg, rs
from datetime import datetime


# --- SESSION AGGREGATES ---
vol_sell_init = 0
vol_buy_init = 0
cost_sell_init = 0
cost_buy_init = 0

buy_volumes=[]
sell_volumes=[]
buy_costs=[]
sell_costs=[]
last_prices=[]


# --------------------------------------------------------------------
# OPEN WEBSOCKET
# --------------------------------------------------------------------
def ws_open(ws):
    print("Connected. Subscribing to PF_SOLUSD Futures...")
    sub = {
        "event": "subscribe",
        "feed": "trade",
        "product_ids": ["PF_SOLUSD"]
    }
    ws.send(json.dumps(sub))



# --------------------------------------------------------------------
# PROCESS A SINGLE FILL (FUTURES TRADE)
# --------------------------------------------------------------------
def process_fill(fill, pair):
    global vol_sell_init, vol_buy_init, cost_buy_init, cost_sell_init
    global buy_volumes, sell_volumes, buy_costs, sell_costs, last_prices

    side = fill["side"]
    vol  = float(fill["qty"])
    price = float(fill["price"])
    cost = vol * price

    # ✔ FIXED: Futures uses "time" in milliseconds
    unix_ms = fill["time"]
    dt = datetime.fromtimestamp(unix_ms / 1000)
    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

    # ---------------- BUY ----------------
    if side == "buy":
        vol_buy_init += vol
        cost_buy_init += cost

        buy_msg = (
            bg.da_green +
            f"{time_str} | {pair} | BUY cost: {round(cost,3)}$ | "
            f"volume: {vol} | @{round(price,3)}$" +
            bg.rs
        )
        print(buy_msg)

        buy_volumes.append(vol)
        sell_volumes.append(0)
        buy_costs.append(cost)
        sell_costs.append(0)

    # ---------------- SELL ----------------
    else:
        vol_sell_init += vol
        cost_sell_init += cost

        sell_msg = (
            bg.da_red +
            f"{time_str} | {pair} | SELL cost: {round(cost,3)}$ | "
            f"volume: {vol} | @{round(price,3)}$" +
            bg.rs
        )
        print(sell_msg)

        buy_volumes.append(0)
        sell_volumes.append(vol)
        buy_costs.append(0)
        sell_costs.append(cost)

    # Track price history
    last_prices.append(price)

    # ---------------- FULL ANALYTICS BLOCK ----------------

    def safe_ratio(size):
        buys = sum(buy_volumes[-size:])
        sells = sum(sell_volumes[-size:])
        if buys + sells == 0:
            return 0
        return 100 * buys / (buys + sells)

    # ---- 50 ----
    last_50 = safe_ratio(50)
    last_50_b = sum(buy_costs[-50:])
    last_50_s = sum(sell_costs[-50:])
    print(fg.li_blue +
          f"Last 50 Buy/Sell Ratio Volume {round(last_50, 2)}% | "
          f"Buys: {round(last_50_b, 2)}$ | Sells: {round(last_50_s, 2)}$" +
          fg.rs)

    # ---- 100 ----
    last_100 = safe_ratio(100)
    last_100_b = sum(buy_costs[-100:])
    last_100_s = sum(sell_costs[-100:])
    print(fg.li_blue +
          f"Last 100 Buy/Sell Ratio Volume {round(last_100, 2)}% | "
          f"Buys: {round(last_100_b, 2)}$ | Sells: {round(last_100_s, 2)}$" +
          fg.rs)

    # ---- 200 ----
    last_200 = safe_ratio(200)
    last_200_b = sum(buy_costs[-200:])
    last_200_s = sum(sell_costs[-200:])
    print(fg.li_blue +
          f"Last 200 Buy/Sell Ratio Volume {round(last_200, 2)}% | "
          f"Buys: {round(last_200_b, 2)}$ | Sells: {round(last_200_s, 2)}$" +
          fg.rs)

    # ---- 500 ----
    last_500 = safe_ratio(500)
    last_500_b = sum(buy_costs[-500:])
    last_500_s = sum(sell_costs[-500:])
    print(fg.li_blue +
          f"Last 500 Buy/Sell Ratio Volume {round(last_500, 2)}% | "
          f"Buys: {round(last_500_b, 2)}$ | Sells: {round(last_500_s, 2)}$" +
          fg.rs)

    # ---- 1000 ----
    last_1000 = safe_ratio(1000)
    last_1000_b = sum(buy_costs[-1000:])
    last_1000_s = sum(sell_costs[-1000:])
    print(fg.li_blue +
          f"Last 1000 Buy/Sell Ratio Volume {round(last_1000, 2)}% | "
          f"Buys: {round(last_1000_b, 2)}$ | Sells: {round(last_1000_s, 2)}$" +
          fg.rs)

    # ---- Price Changes ----
    def price_change(size):
        if len(last_prices) < size:
            return 0
        start = last_prices[-size]
        now = last_prices[-1]
        return round(((now - start) / start) * 100, 1)

    print(f"Price change, last 50 {price_change(50)}")
    print(f"Price change, last 100 {price_change(100)}")
    print(f"Price change, last 200 {price_change(200)}")
    print(f"Price change, last 500 {price_change(500)}")
    print(f"Price change, last 1000 {price_change(1000)}")

    if len(last_prices) > 1:
        session_change = round(((last_prices[-1] - last_prices[0]) / last_prices[0]) * 100, 1)
        print(f"Price change, session {session_change}")

    # ---- Session Buy/Sell Summary ----
    total_ratio = (vol_buy_init / (vol_buy_init + vol_sell_init)) if (vol_buy_init + vol_sell_init) else 0

    print(
        fg.blue +
        f"Session start Buy/Sell Ratio Volume {round(total_ratio * 100,3)}% "
        f"| Total buys {round(cost_buy_init,3)}$ | Total sells {round(cost_sell_init,3)}$"
        + fg.rs
    )



# --------------------------------------------------------------------
# MAIN MESSAGE HANDLER
# --------------------------------------------------------------------
def handle_message(ws, message):
    data = json.loads(message)

    if not isinstance(data, dict):
        return

    if data.get("feed") != "trade":
        return

    pair = data.get("product_id", "PF_SOLUSD")

    # Case 1 — Single fill
    if data.get("type") == "fill":
        process_fill(data, pair)
        return

    # Case 2 — Multi-fill message
    if "fills" in data:
        for fill in data["fills"]:
            process_fill(fill, pair)
        return



def ws_message(ws, message):
    try:
        handle_message(ws, message)
    except Exception as e:
        print("❌ EXCEPTION:", e)
        print("❌ MESSAGE:", message)



# --------------------------------------------------------------------
# RUN
# --------------------------------------------------------------------
ws = websocket.WebSocketApp(
    "wss://futures.kraken.com/ws/v1",
    on_open=ws_open,
    on_message=ws_message
)

ws.run_forever()