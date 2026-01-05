# panels/panel_1.py
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws
import time


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                "Multi-Coin Live Trades (Time-Synced) - Normalized",
                className="panel-title"
            ),
            html.Div(
                dcc.Graph(
                    id="panel1-multicoin",
                    config={"displayModeBar": False},
                    style={"width": "100%", "height": "100%"}
                ),
                className="panel-graph"
            ),
            dcc.Interval(id="panel1-interval", interval=1000, n_intervals=0)
        ]
    )


def register_callbacks(app):
    
    @app.callback(
        Output("panel1-multicoin", "figure"),
        Input("panel1-interval", "n_intervals")
    )
    def update_multicoin(_):
        
        fig = go.Figure()
        
        # Coin configurations
        coins = {
            "PF_XBTUSD": {"name": "BTC", "color": "#F7931A"},
            "PF_ETHUSD": {"name": "ETH", "color": "#627EEA"},
            "PF_SOLUSD": {"name": "SOL", "color": "#14F195"},
            "PF_ADAUSD": {"name": "ADA", "color": "#0033AD"}
        }
        
        # Find the LATEST start time across all coins (so all lines start together)
        # This ensures we only show the time window where ALL coins have data
        latest_start_time = None
        current_time = time.time()
        
        for product_id in coins.keys():
            trades = list(ws.MULTI_COIN_TRADES[product_id])
            if trades:
                first_ts = trades[0][0]
                if latest_start_time is None or first_ts > latest_start_time:
                    latest_start_time = first_ts
        
        if latest_start_time is None:
            return go.Figure().update_layout(template="plotly_dark")
        
        # Plot each coin with time-based x-axis, starting from common time
        for product_id, config in coins.items():
            trades = list(ws.MULTI_COIN_TRADES[product_id])
            
            if not trades:
                continue
            
            # Filter trades to only include those after latest_start_time
            filtered_trades = [(ts, price) for ts, price in trades if ts >= latest_start_time]
            
            if not filtered_trades:
                continue
            
            # Extract timestamps and prices
            timestamps = [t[0] for t in filtered_trades]
            prices = [t[1] for t in filtered_trades]
            
            if not prices:
                continue
            
            # Use the FIRST price in the common window as reference (not the old reference)
            ref_price = prices[0]
            
            # Normalize prices to percentage change
            normalized = [((p - ref_price) / ref_price) * 100 for p in prices]
            
            # Convert timestamps to seconds from latest_start_time
            x_vals = [(ts - latest_start_time) for ts in timestamps]
            
            # Forward fill: carry last price to current time
            last_price_normalized = normalized[-1]
            current_x = current_time - latest_start_time
            
            # Add current time point with last known price
            x_vals.append(current_x)
            normalized.append(last_price_normalized)
            
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=normalized,
                mode="lines",
                name=config["name"],
                line=dict(color=config["color"], width=2, shape='hv'),  # 'hv' = step line (horizontal then vertical)
                hovertemplate=f"<b>{config['name']}</b><br>" +
                             "Time: %{x:.0f}s<br>" +
                             "Change: %{y:.2f}%<br>" +
                             "<extra></extra>"
            ))
        
        # Add zero reference line
        fig.add_hline(
            y=0, 
            line=dict(color="gray", width=1, dash="dot"),
            annotation_text="Reference (0%)"
        )
        
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=60, r=40, t=40, b=40),
            xaxis_title="Time (seconds from start)",
            yaxis_title="Price Change (%)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode="x unified"
        )
        
        return fig