import requests
import pandas as pd

KRAKEN_URL = "https://api.kraken.com/0/public/OHLC"

def get_ohlc(pair="XXBTZUSD", interval=60):
    """
    Fetch OHLC data from Kraken REST API.
    interval example: 1 = 1 min, 60 = 1 hour, 1440 = daily.
    """
    params = {"pair": pair, "interval": interval}
    r = requests.get(KRAKEN_URL, params=params).json()

    # Kraken returns {"result": {"XXBTZUSD": [...]}}
    pair_key = list(r["result"].keys())[0]
    data = r["result"][pair_key]

    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "vwap", "volume", "count"
    ])

    df["time"] = pd.to_datetime(df["time"], unit='s')
    df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)

    return df
