# panels/panel_3.py
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws
import numpy as np
from collections import deque
import time

# Store order book history for bookmap visualization
BOOKMAP_HISTORY = deque(maxlen=300)  # Keep 5 minutes at 1-second intervals
SEEN_TRADE_TIMES = set()  # Track which trades we've already processed

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
        
        global BOOKMAP_HISTORY, SEEN_TRADE_TIMES
        
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
        
        # Aggregate order book into price buckets
        bucket_size = 0.25
        bid_dict = {}
        for price, vol in bids:
            bucket = round(price / bucket_size) * bucket_size
            bid_dict[bucket] = bid_dict.get(bucket, 0) + vol
        
        ask_dict = {}
        for price, vol in asks:
            bucket = round(price / bucket_size) * bucket_size
            ask_dict[bucket] = ask_dict.get(bucket, 0) + vol
        
        # Collect new trades for this snapshot
        new_trades = []
        if ws.BOOKMAP_TRADES:
            for trade in ws.BOOKMAP_TRADES:
                trade_id = (trade["time"], trade["price"], trade["volume"])
                if trade_id not in SEEN_TRADE_TIMES:
                    SEEN_TRADE_TIMES.add(trade_id)
                    new_trades.append({
                        "time": trade["time"],
                        "price": trade["price"],
                        "volume": trade["volume"],
                        "side": trade["side"]
                    })
        
        # Clean up old seen trades (keep memory bounded)
        if len(SEEN_TRADE_TIMES) > 10000:
            SEEN_TRADE_TIMES.clear()
        
        # Store snapshot with trades
        BOOKMAP_HISTORY.append({
            "time": current_time,
            "bids": bid_dict.copy(),
            "asks": ask_dict.copy(),
            "price": current_price,
            "trades": new_trades
        })
        
        if len(BOOKMAP_HISTORY) < 2:
            return go.Figure().update_layout(template="plotly_dark", title="Collecting data...")
        
        # Focus on ACTIVE trading range (near current price)
        if bids and asks:
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            mid_price = (best_bid + best_ask) / 2
            
            price_range_pct = 0.02
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
        
        # Also collect all trades with their x-index
        all_trades = []
        
        for t_idx, snapshot in enumerate(BOOKMAP_HISTORY):
            for p_idx, price in enumerate(all_prices):
                bid_vol = snapshot["bids"].get(price, 0)
                ask_vol = snapshot["asks"].get(price, 0)
                liquidity_matrix[p_idx, t_idx] = bid_vol + ask_vol
            
            # Add trades from this snapshot at this x-index
            for trade in snapshot.get("trades", []):
                all_trades.append((t_idx, trade["price"], trade["volume"], trade["side"]))
        
        # Apply log scale for better visualization
        liquidity_log = np.log1p(liquidity_matrix)
        
        fig = go.Figure()
        
        # Add liquidity heatmap
        fig.add_trace(go.Heatmap(
            z=liquidity_log,
            x=list(range(num_times)),
            y=all_prices,
            colorscale=[
                [0.0, 'rgb(0, 20, 40)'],
                [0.3, 'rgb(0, 100, 150)'],
                [0.6, 'rgb(100, 200, 255)'],
                [0.8, 'rgb(255, 200, 0)'],
                [1.0, 'rgb(255, 100, 0)']
            ],
            showscale=False,
            hovertemplate='Time: %{x}<br>Price: $%{y:.2f}<br>Liquidity: %{customdata:.0f}<extra></extra>',
            customdata=liquidity_matrix,
            opacity=0.8
        ))
        
        # Add trade markers
        if all_trades:
            x_vals, y_vals, volumes, sides = zip(*all_trades)
            
            # Calculate marker sizes based on volume
            if max(volumes) > 0:
                min_size = 5
                max_size = 30
                log_volumes = [np.log1p(v) for v in volumes]
                max_log = max(log_volumes) if max(log_volumes) > 0 else 1
                sizes = [min_size + (lv / max_log) * (max_size - min_size) for lv in log_volumes]
            else:
                sizes = [8] * len(volumes)
            
            # Color based on trade side
            colors = ['lime' if s == 'buy' else 'red' for s in sides]
            
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='markers',
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
                autorange=True
            ),
            plot_bgcolor='black',
            hovermode='closest'
        )
        
        return fig