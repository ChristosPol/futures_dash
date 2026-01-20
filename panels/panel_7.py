# panels/panel_7.py
# Support/Resistance Levels from Historical Candlesticks (All Timeframes)
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import time

# Cache for OHLC data
OHLC_CACHE = {
    "last_update": 0,
    "levels": {}
}

UPDATE_INTERVAL = 3600  # Update every hour (3600 seconds)

# Kraken available intervals: 1, 5, 15, 30, 60
# Minutes:                    1m, 5m, 15m, 30m, 1h
TIMEFRAMES = {
    "1m": {"interval": 1, "label": "1 Min"},
    "5m": {"interval": 5, "label": "5 Min"},
    "15m": {"interval": 15, "label": "15 Min"},
    "30m": {"interval": 30, "label": "30 Min"},
    "1H": {"interval": 60, "label": "1 Hour"},
}


def fetch_ohlc(pair="SOLUSD", interval=60):
    """
    Fetch OHLC data from Kraken REST API.
    Kraken intervals: 1, 5, 15, 30, 60, 240, 1440, 10080, 21600
    """
    url = "https://api.kraken.com/0/public/OHLC"
    params = {"pair": pair, "interval": interval}
    
    try:
        r = requests.get(url, params=params, timeout=10).json()
        
        if "result" not in r:
            print(f"Kraken API error: {r}")
            return None
        
        # Kraken returns {"result": {"XXBTZUSD": [...], "last": ...}}
        pair_key = [k for k in r["result"].keys() if k != "last"][0]
        data = r["result"][pair_key]
        
        df = pd.DataFrame(data, columns=[
            "time", "open", "high", "low", "close", "vwap", "volume", "count"
        ])
        
        df["time"] = pd.to_datetime(df["time"], unit='s')
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        df["volume"] = df["volume"].astype(float)
        
        return df
    except Exception as e:
        print(f"Error fetching OHLC (interval={interval}): {e}")
        return None


def calculate_support_resistance(df, n=10):
    """
    Calculate support and resistance from close prices.
    - Support: median of n smallest close values
    - Resistance: median of n largest close values
    """
    if df is None or len(df) < n:
        return None, None
    
    closes = df["close"].values
    
    # Sort and get smallest/largest
    sorted_closes = np.sort(closes)
    
    smallest_n = sorted_closes[:n]
    largest_n = sorted_closes[-n:]
    
    support = np.median(smallest_n)
    resistance = np.median(largest_n)
    
    return support, resistance


def update_levels():
    """Update support/resistance levels from Kraken data for all timeframes."""
    global OHLC_CACHE
    
    current_time = time.time()
    
    # Only update if cache is stale
    if current_time - OHLC_CACHE["last_update"] < UPDATE_INTERVAL:
        return OHLC_CACHE["levels"]
    
    print("Updating S/R levels from Kraken (all timeframes)...")
    
    levels = {}
    
    # Fetch data for each timeframe
    for tf_key, tf_config in TIMEFRAMES.items():
        df = fetch_ohlc(pair="SOLUSD", interval=tf_config["interval"])
        if df is not None and len(df) >= 10:
            support, resistance = calculate_support_resistance(df, n=10)
            if support and resistance:
                levels[tf_key] = {
                    "support": support,
                    "resistance": resistance,
                    "candles": len(df),
                    "label": tf_config["label"]
                }
                print(f"  {tf_key}: S=${support:.2f}, R=${resistance:.2f} ({len(df)} candles)")
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
    
    OHLC_CACHE["levels"] = levels
    OHLC_CACHE["last_update"] = current_time
    
    print(f"S/R Levels updated for {len(levels)} timeframes")
    
    return levels


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                "Support & Resistance Levels — SOLUSD (All Timeframes)",
                className="panel-title"
            ),
            dcc.Graph(
                id="panel7-sr-levels",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panel7-interval", interval=60000, n_intervals=0)  # Update display every 60s
        ]
    )


def register_callbacks(app):

    @app.callback(
        Output("panel7-sr-levels", "figure"),
        Input("panel7-interval", "n_intervals")
    )
    def update(_):
        
        # Get/update levels
        levels = update_levels()
        
        if not levels:
            return go.Figure().update_layout(
                template="plotly_dark",
                title="Fetching S/R levels from Kraken..."
            )
        
        # Current price from websocket
        current_price = ws.LAST_PRICE if ws.LAST_PRICE else 0
        
        fig = go.Figure()
        
        # Create price scale for y-axis
        all_prices = [current_price] if current_price else []
        for tf, data in levels.items():
            all_prices.extend([data["support"], data["resistance"]])
        
        if not all_prices:
            return go.Figure().update_layout(template="plotly_dark", title="No data")
        
        min_price = min(all_prices) * 0.98
        max_price = max(all_prices) * 1.02
        
        # Order timeframes from shortest to longest
        tf_order = ["1m", "5m", "15m", "30m", "1H"]
        available_tfs = [tf for tf in tf_order if tf in levels]
        
        # X-axis categories
        categories = [levels[tf]["label"] for tf in available_tfs]
        
        # Collect support/resistance prices
        support_prices = [levels[tf]["support"] for tf in available_tfs]
        resistance_prices = [levels[tf]["resistance"] for tf in available_tfs]
        candle_counts = [levels[tf]["candles"] for tf in available_tfs]
        
        # Support markers (green triangles)
        fig.add_trace(go.Scatter(
            x=categories,
            y=support_prices,
            mode='markers+text',
            name='Support',
            marker=dict(size=15, color='lime', symbol='triangle-up'),
            text=[f"${p:.2f}" for p in support_prices],
            textposition='bottom center',
            textfont=dict(size=9, color='lime'),
            customdata=candle_counts,
            hovertemplate='<b>Support</b><br>%{x}<br>$%{y:.2f}<br>Candles: %{customdata}<extra></extra>'
        ))
        
        # Resistance markers (red triangles)
        fig.add_trace(go.Scatter(
            x=categories,
            y=resistance_prices,
            mode='markers+text',
            name='Resistance',
            marker=dict(size=15, color='red', symbol='triangle-down'),
            text=[f"${p:.2f}" for p in resistance_prices],
            textposition='top center',
            textfont=dict(size=9, color='red'),
            customdata=candle_counts,
            hovertemplate='<b>Resistance</b><br>%{x}<br>$%{y:.2f}<br>Candles: %{customdata}<extra></extra>'
        ))
        
        # Connect support levels with a line
        fig.add_trace(go.Scatter(
            x=categories,
            y=support_prices,
            mode='lines',
            name='Support Trend',
            line=dict(color='rgba(0, 255, 0, 0.3)', width=1, dash='dot'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Connect resistance levels with a line
        fig.add_trace(go.Scatter(
            x=categories,
            y=resistance_prices,
            mode='lines',
            name='Resistance Trend',
            line=dict(color='rgba(255, 0, 0, 0.3)', width=1, dash='dot'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Current price line
        if current_price:
            fig.add_hline(
                y=current_price,
                line=dict(color='white', width=2, dash='dot'),
                annotation_text=f"Current: ${current_price:.2f}",
                annotation_position="right",
                annotation_font=dict(size=10, color='white')
            )
        
        # Calculate average S/R across all timeframes
        avg_support = np.mean(support_prices)
        avg_resistance = np.mean(resistance_prices)
        
        # Add average lines
        fig.add_hline(
            y=avg_support,
            line=dict(color='lime', width=1, dash='dash'),
            annotation_text=f"Avg S: ${avg_support:.2f}",
            annotation_position="left",
            annotation_font=dict(size=9, color='lime'),
            opacity=0.5
        )
        
        fig.add_hline(
            y=avg_resistance,
            line=dict(color='red', width=1, dash='dash'),
            annotation_text=f"Avg R: ${avg_resistance:.2f}",
            annotation_position="left",
            annotation_font=dict(size=9, color='red'),
            opacity=0.5
        )
        
        last_update = datetime.fromtimestamp(OHLC_CACHE["last_update"]).strftime("%H:%M:%S") if OHLC_CACHE["last_update"] else "Never"
        
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=80, r=40, t=30, b=50),
            yaxis=dict(
                title="Price (USD)",
                range=[min_price, max_price],
                tickformat='$.2f',
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)'
            ),
            xaxis=dict(
                title="",
                showgrid=False,
                tickangle=-45
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            annotations=[
                dict(
                    x=0.5,
                    y=-0.18,
                    xref="paper",
                    yref="paper",
                    text=f"Updated: {last_update} | Median of 10 extreme closes per timeframe",
                    showarrow=False,
                    font=dict(size=9, color='gray')
                )
            ],
            plot_bgcolor='black'
        )
        
        return fig