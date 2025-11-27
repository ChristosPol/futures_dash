def add_sma(df, period=20, column="close"):
    sma_col = f"SMA{period}"
    df[sma_col] = df[column].rolling(period).mean()
    return df

def add_all_smas(df):
    df["SMA20"]  = df["close"].rolling(20).mean()
    df["SMA50"]  = df["close"].rolling(50).mean()
    df["SMA200"] = df["close"].rolling(200).mean()
    return df
