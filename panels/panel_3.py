# panels/panel_3.py
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws
import numpy as np
from collections import deque
import time

# Store volume history over time for heatmap
# Structure: {price_level: deque([(timestamp, buy_vol, sell_vol), ...], maxlen=100)}
VOLUME_HISTORY = {}
MAX_TIME_POINTS = 100  # Keep last 100 time points

def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                "Order Flow Heatmap (Bookmap Style) — PF_SOLUSD",
                className="panel-title"
            ),
            dcc.Graph(
                id="panel3-heatmap",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panel3-interval", interval=1000, n_intervals=0)
        ]
    )

def register_callbacks(app):

    @app.callback(
        Output("panel3-heatmap", "figure"),
        Input("panel3-interval", "n_intervals")
    )
    def update_heatmap(_):
        
        global VOLUME_HISTORY
        
        if not ws.PRICE_BUCKETS:
            return go.Figure().update_layout(
                template="plotly_dark",
                title="Waiting for data..."
            )

        current_time = time.time()
        
        # Update volume history for each price bucket
        for price, volumes in ws.PRICE_BUCKETS.items():
            if price not in VOLUME_HISTORY:
                VOLUME_HISTORY[price] = deque(maxlen=MAX_TIME_POINTS)
            
            buy_vol = volumes.get("buy", 0)
            sell_vol = volumes.get("sell", 0)
            
            # Add current snapshot
            VOLUME_HISTORY[price].append((current_time, buy_vol, sell_vol))
        
        # Get all price levels (sorted)
        all_prices = sorted(VOLUME_HISTORY.keys())
        
        if not all_prices:
            return go.Figure().update_layout(template="plotly_dark")
        
        # Get all timestamps from the most recent price level
        if all_prices and VOLUME_HISTORY[all_prices[0]]:
            timestamps = [t for t, _, _ in VOLUME_HISTORY[all_prices[0]]]
        else:
            return go.Figure().update_layout(template="plotly_dark")
        
        # Build 2D matrix for heatmap
        # Rows = price levels, Columns = time points
        num_prices = len(all_prices)
        num_times = len(timestamps)
        
        # Create separate matrices for buys and sells
        buy_matrix = np.zeros((num_prices, num_times))
        sell_matrix = np.zeros((num_prices, num_times))
        
        for i, price in enumerate(all_prices):
            history = list(VOLUME_HISTORY[price])
            for j in range(min(len(history), num_times)):
                _, buy_vol, sell_vol = history[j]
                buy_matrix[i, j] = buy_vol
                sell_matrix[i, j] = sell_vol
        
        # Net volume (positive = more buys, negative = more sells)
        net_matrix = buy_matrix - sell_matrix
        
        # Normalize for better color scaling
        max_abs = np.max(np.abs(net_matrix)) if np.max(np.abs(net_matrix)) > 0 else 1
        normalized = net_matrix / max_abs
        
        # Create time labels (relative seconds)
        time_labels = [f"{i}s" for i in range(num_times)]
        price_labels = [f"${p:.2f}" for p in all_prices]
        
        fig = go.Figure()
        
        # Add heatmap
        fig.add_trace(go.Heatmap(
            z=normalized,
            x=time_labels,
            y=price_labels,
            colorscale=[
                [0.0, 'rgb(200, 0, 0)'],    # Dark red (heavy selling)
                [0.3, 'rgb(255, 50, 50)'],  # Red
                [0.45, 'rgb(50, 50, 50)'],  # Dark gray (neutral)
                [0.55, 'rgb(50, 50, 50)'],  # Dark gray (neutral)
                [0.7, 'rgb(50, 255, 50)'],  # Green
                [1.0, 'rgb(0, 200, 0)']     # Dark green (heavy buying)
            ],
            showscale=True,
            colorbar=dict(
                title="Volume Imbalance",
                x=1.02,
                tickmode="array",
                tickvals=[-1, -0.5, 0, 0.5, 1],
                ticktext=["Sell", "Sell", "Neutral", "Buy", "Buy"]
            ),
            hovertemplate='Time: %{x}<br>Price: %{y}<br>Net: %{z:.2f}<extra></extra>'
        ))
        
        # Add current price line
        if ws.LAST_PRICE:
            # Find closest price in our list
            closest_idx = min(range(len(all_prices)), 
                            key=lambda i: abs(all_prices[i] - ws.LAST_PRICE))
            
            fig.add_shape(
                type="line",
                x0=0,
                x1=num_times - 1,
                y0=closest_idx,
                y1=closest_idx,
                line=dict(color="yellow", width=3),
                xref="x",
                yref="y"
            )
        
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=80, r=120, t=40, b=60),
            xaxis_title="Time (recent →)",
            yaxis_title="Price Levels",
            plot_bgcolor='black',
            xaxis=dict(
                showgrid=False,
                tickmode='linear',
                tick0=0,
                dtick=10
            ),
            yaxis=dict(
                showgrid=False
            )
        )
        
        return fig