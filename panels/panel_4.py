# panels/panel_4.py
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws
import numpy as np
from collections import deque
import time

# Store order book history over time
ORDER_BOOK_HISTORY = deque(maxlen=100)

PRICE_BUCKET_SIZE = 0.50  # 50 cents buckets

def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                "Cumulative Order Book Depth (0.50 Buckets) — PF_SOLUSD",
                className="panel-title"
            ),
            html.Div(
                dcc.Graph(
                    id="panel4-heatmap",
                    config={"displayModeBar": False},
                    style={"width": "100%", "height": "100%"}
                ),
                className="panel-graph"
            ),
            dcc.Interval(id="panel4-interval", interval=1000, n_intervals=0)
        ]
    )

def _bucket_price(price):
    """Round price to nearest bucket."""
    return round(price / PRICE_BUCKET_SIZE) * PRICE_BUCKET_SIZE

def register_callbacks(app):

    @app.callback(
        Output("panel4-heatmap", "figure"),
        Input("panel4-interval", "n_intervals")
    )
    def update_heatmap(_):
        
        global ORDER_BOOK_HISTORY
        
        # Get current order book snapshot
        bids = ws.ORDER_BOOK.get("bids", [])
        asks = ws.ORDER_BOOK.get("asks", [])
        
        if not bids or not asks:
            return go.Figure().update_layout(
                template="plotly_dark",
                title="Waiting for order book data..."
            )
        
        current_time = time.time()
        
        # Get current price range for filtering
        if bids and asks:
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            mid_price = (best_bid + best_ask) / 2
            
            # Only keep buckets within +/- $5 of mid price
            price_range = 5.0
        else:
            return go.Figure().update_layout(template="plotly_dark")
        
        # Aggregate order book into buckets (filter outliers)
        bid_buckets = {}
        for price, vol in bids:
            if abs(price - mid_price) <= price_range:
                bucket = _bucket_price(price)
                bid_buckets[bucket] = bid_buckets.get(bucket, 0) + vol
        
        ask_buckets = {}
        for price, vol in asks:
            if abs(price - mid_price) <= price_range:
                bucket = _bucket_price(price)
                ask_buckets[bucket] = ask_buckets.get(bucket, 0) + vol
        
        # Store snapshot
        ORDER_BOOK_HISTORY.append((current_time, bid_buckets.copy(), ask_buckets.copy(), mid_price))
        
        if len(ORDER_BOOK_HISTORY) < 2:
            return go.Figure().update_layout(
                template="plotly_dark",
                title="Collecting data..."
            )
        
        # Get all unique price buckets across recent snapshots (within range)
        all_buckets = set()
        for _, bids_snap, asks_snap, hist_mid in ORDER_BOOK_HISTORY:
            for bucket in bids_snap.keys():
                if abs(bucket - mid_price) <= price_range:
                    all_buckets.add(bucket)
            for bucket in asks_snap.keys():
                if abs(bucket - mid_price) <= price_range:
                    all_buckets.add(bucket)
        
        all_buckets = sorted(all_buckets)
        
        if not all_buckets:
            return go.Figure().update_layout(template="plotly_dark")
        
        # Build matrices for cumulative visualization
        num_buckets = len(all_buckets)
        num_times = len(ORDER_BOOK_HISTORY)
        
        bid_cumulative_matrix = np.zeros((num_buckets, num_times))
        ask_cumulative_matrix = np.zeros((num_buckets, num_times))
        
        timestamps = []
        
        for t_idx, (ts, bids_snap, asks_snap, _) in enumerate(ORDER_BOOK_HISTORY):
            timestamps.append(ts)
            
            # Calculate cumulative volumes (from lowest to highest)
            bid_cumsum = 0
            for b_idx in range(num_buckets):
                bucket = all_buckets[b_idx]
                bid_vol = bids_snap.get(bucket, 0)
                bid_cumsum += bid_vol
                bid_cumulative_matrix[b_idx, t_idx] = bid_cumsum
            
            # Calculate cumulative volumes (from highest to lowest)
            ask_cumsum = 0
            for b_idx in range(num_buckets - 1, -1, -1):
                bucket = all_buckets[b_idx]
                ask_vol = asks_snap.get(bucket, 0)
                ask_cumsum += ask_vol
                ask_cumulative_matrix[b_idx, t_idx] = ask_cumsum
        
        # Store raw values for text display
        combined_matrix_raw = bid_cumulative_matrix - ask_cumulative_matrix
        
        # Create text annotations (show every 5th time point to avoid clutter)
        text_matrix = []
        for b_idx in range(num_buckets):
            row_text = []
            for t_idx in range(num_times):
                val = combined_matrix_raw[b_idx, t_idx]
                # Only show text every 10 seconds and if value is significant
                if t_idx % 10 == 0 and abs(val) > 50:
                    if val > 0:
                        row_text.append(f"{int(val)}")
                    else:
                        row_text.append(f"{int(val)}")
                else:
                    row_text.append("")
            text_matrix.append(row_text)
        
        # Normalize for color scale (log scale)
        def log_normalize(val):
            if val > 0:
                return np.log1p(val)
            elif val < 0:
                return -np.log1p(abs(val))
            return 0
        
        normalized = np.vectorize(log_normalize)(combined_matrix_raw)
        
        # Create labels
        time_labels = [f"-{num_times - i}s" for i in range(num_times)]
        bucket_labels = [f"${b:.2f}" for b in all_buckets]
        
        fig = go.Figure()
        
        # Add heatmap with text annotations
        fig.add_trace(go.Heatmap(
            z=normalized,
            x=time_labels,
            y=bucket_labels,
            text=text_matrix,
            texttemplate="%{text}",
            textfont={"size": 8, "color": "white"},
            colorscale=[
                [0.0, 'rgb(139, 0, 0)'],     # Dark red (cumulative asks)
                [0.35, 'rgb(255, 100, 100)'], # Light red
                [0.48, 'rgb(30, 30, 30)'],    # Dark gray (neutral)
                [0.52, 'rgb(30, 30, 30)'],    # Dark gray (neutral)
                [0.65, 'rgb(100, 255, 100)'], # Light green
                [1.0, 'rgb(0, 139, 0)']       # Dark green (cumulative bids)
            ],
            showscale=True,
            colorbar=dict(
                title="Log Scale<br>Depth",
                x=1.02,
                tickmode="array",
                tickvals=[-3, -1.5, 0, 1.5, 3],
                ticktext=["Ask Wall", "Asks", "Spread", "Bids", "Bid Wall"]
            ),
            hovertemplate='Time: %{x}<br>Price: %{y}<br>Raw Depth: %{customdata:.0f} SOL<extra></extra>',
            customdata=combined_matrix_raw
        ))
        
        # Add spread zone (current bid-ask spread)
        if bids and asks:
            best_bid_bucket = _bucket_price(best_bid)
            best_ask_bucket = _bucket_price(best_ask)
            
            if best_bid_bucket in all_buckets and best_ask_bucket in all_buckets:
                bid_idx = all_buckets.index(best_bid_bucket)
                ask_idx = all_buckets.index(best_ask_bucket)
                
                fig.add_shape(
                    type="rect",
                    x0=0,
                    x1=num_times - 1,
                    y0=bid_idx,
                    y1=ask_idx,
                    line=dict(color="yellow", width=1, dash="dot"),
                    fillcolor="rgba(255, 255, 0, 0.08)",
                    xref="x",
                    yref="y"
                )
        
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=80, r=120, t=40, b=60),
            xaxis_title="Time (history ← | now →)",
            yaxis_title="Price Buckets ($0.50)",
            plot_bgcolor='black',
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)'
            )
        )
        
        return fig