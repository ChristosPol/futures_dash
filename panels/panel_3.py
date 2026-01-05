# panels/panel_3.py
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws
import numpy as np
from collections import deque
import time

# Store order book history for bookmap visualization
BOOKMAP_HISTORY = deque(maxlen=300)  # Keep 5 minutes at 1-second intervals
ACTUAL_TRADES = deque(maxlen=500)  # Store ONLY actual trades (timestamp, price, volume, side)
LAST_TRADE_TIME = 0  # Track last trade timestamp to detect new ones

def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                "Bookmap — Order Flow Visualization — PF_SOLUSD",
                className="panel-title"
            ),
            dcc.Graph(
                id="panel3-bookmap",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panel3-interval", interval=1000, n_intervals=0)
        ]
    )

def register_callbacks(app):

    @app.callback(
        Output("panel3-bookmap", "figure"),
        Input("panel3-interval", "n_intervals")
    )
    def update_bookmap(_):
        
        global BOOKMAP_HISTORY, ACTUAL_TRADES, LAST_TRADE_TIME
        
        # Get current order book
        bids = ws.ORDER_BOOK.get("bids", [])
        asks = ws.ORDER_BOOK.get("asks", [])
        
        if not bids or not asks:
            return go.Figure().update_layout(
                template="plotly_dark",
                title="Waiting for order book data..."
            )
        
        current_time = time.time()
        current_price = ws.LAST_PRICE if ws.LAST_PRICE else (bids[0][0] + asks[0][0]) / 2
        
        # Check for NEW trades - get all trades newer than last recorded
        if ws.LAST_TRADES:
            for trade in ws.LAST_TRADES:
                trade_time = trade["time"]
                # Only add trades we haven't seen yet
                if trade_time > LAST_TRADE_TIME:
                    ACTUAL_TRADES.append((
                        trade_time,
                        trade["price"],
                        trade["volume"],
                        trade["side"]
                    ))
            # Update last trade time to the most recent
            LAST_TRADE_TIME = max(t["time"] for t in ws.LAST_TRADES)
        
        # Aggregate order book into price buckets
        bucket_size = 0.25
        bid_dict = {}
        for price, vol in bids:  # Use ALL bids
            bucket = round(price / bucket_size) * bucket_size
            bid_dict[bucket] = bid_dict.get(bucket, 0) + vol
        
        ask_dict = {}
        for price, vol in asks:  # Use ALL asks
            bucket = round(price / bucket_size) * bucket_size
            ask_dict[bucket] = ask_dict.get(bucket, 0) + vol
        
        # Store snapshot
        BOOKMAP_HISTORY.append({
            "time": current_time,
            "bids": bid_dict.copy(),
            "asks": ask_dict.copy(),
            "price": current_price
        })
        
        if len(BOOKMAP_HISTORY) < 2:
            return go.Figure().update_layout(template="plotly_dark", title="Collecting data...")
        
        # Focus on ACTIVE trading range (near current price), not full order book depth
        if bids and asks:
            # Use best bid/ask (top of book) as reference
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            mid_price = (best_bid + best_ask) / 2
            
            # Show ±2% around mid price (adjustable range)
            price_range_pct = 0.02  # 2% above and below
            min_bid_price = mid_price * (1 - price_range_pct)
            max_ask_price = mid_price * (1 + price_range_pct)
        else:
            return go.Figure().update_layout(template="plotly_dark")
        
        # Create ALL price levels between min and max
        all_prices = []
        p = round(min_bid_price / bucket_size) * bucket_size
        while p <= max_ask_price:
            all_prices.append(round(p, 2))
            p += bucket_size
        
        if not all_prices:
            return go.Figure().update_layout(template="plotly_dark")
        
        # Build heatmap matrix
        num_prices = len(all_prices)
        num_times = len(BOOKMAP_HISTORY)
        
        liquidity_matrix = np.zeros((num_prices, num_times))
        timestamps = []
        
        for t_idx, snapshot in enumerate(BOOKMAP_HISTORY):
            timestamps.append(snapshot["time"])
            
            for p_idx, price in enumerate(all_prices):
                bid_vol = snapshot["bids"].get(price, 0)
                ask_vol = snapshot["asks"].get(price, 0)
                # Total liquidity at this price level
                liquidity_matrix[p_idx, t_idx] = bid_vol + ask_vol
        
        # Apply log scale for better visualization
        liquidity_log = np.log1p(liquidity_matrix)
        
        fig = go.Figure()
        
        # Add liquidity heatmap
        fig.add_trace(go.Heatmap(
            z=liquidity_log,
            x=list(range(num_times)),
            y=all_prices,
            colorscale=[
                [0.0, 'rgb(0, 20, 40)'],      # Dark blue (low/no liquidity)
                [0.3, 'rgb(0, 100, 150)'],    # Medium blue
                [0.6, 'rgb(100, 200, 255)'],  # Light blue
                [0.8, 'rgb(255, 200, 0)'],    # Yellow (high liquidity)
                [1.0, 'rgb(255, 100, 0)']     # Orange (very high)
            ],
            showscale=False,
            hovertemplate='Time: %{x}<br>Price: $%{y:.2f}<br>Liquidity: %{customdata:.0f}<extra></extra>',
            customdata=liquidity_matrix,
            opacity=0.8
        ))
        
        # Add trade markers (ONLY where actual trades occurred)
        if len(ACTUAL_TRADES) > 0 and len(timestamps) > 0:
            min_time = timestamps[0]
            max_time = timestamps[-1]
            
            # Filter trades within our time window
            valid_trades = []
            for t, price, volume, side in ACTUAL_TRADES:
                if min_time <= t <= max_time:
                    # Map timestamp to x-axis index
                    closest_idx = min(range(len(timestamps)), 
                                    key=lambda i: abs(timestamps[i] - t))
                    valid_trades.append((closest_idx, price, volume, side))
            
            if valid_trades:
                x_vals, y_vals, volumes, sides = zip(*valid_trades)
                
                # Calculate marker sizes based on volume (min 5, max 30)
                if max(volumes) > 0:
                    min_size = 5
                    max_size = 30
                    log_volumes = [np.log1p(v) for v in volumes]
                    max_log = max(log_volumes) if max(log_volumes) > 0 else 1
                    sizes = [min_size + (lv / max_log) * (max_size - min_size) for lv in log_volumes]
                else:
                    sizes = [8] * len(volumes)
                
                # Color based on trade side (buy=green, sell=red)
                colors = ['lime' if s == 'buy' else 'red' for s in sides]
                
                fig.add_trace(go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode='markers',  # ONLY markers, no lines
                    marker=dict(
                        size=sizes,
                        color=colors,
                        line=dict(color='white', width=1),
                        opacity=0.9
                    ),
                    name='Trades',
                    showlegend=False,
                    customdata=list(zip(volumes, sides)),
                    hovertemplate='Price: $%{y:.2f}<br>Volume: %{customdata[0]:.2f}<br>Side: %{customdata[1]}<extra></extra>'
                ))
        
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=60, r=20, t=10, b=40),
            xaxis=dict(
                title="Time",
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.1)',
                showticklabels=True,
                tickmode='linear',
                tick0=0,
                dtick=30,
                ticktext=[f"-{num_times - i}s" for i in range(0, num_times, 30)],
                tickvals=list(range(0, num_times, 30))
            ),
            yaxis=dict(
                title="Price",
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.1)',
                tickformat='$.2f',
                autorange=True  # Auto-adjust to show full range
            ),
            plot_bgcolor='black',
            hovermode='closest'
        )
        
        return fig