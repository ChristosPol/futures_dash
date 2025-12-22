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
                "Multi-Coin Live Trades (Last 2000) - Normalized",
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
        
        # Find the earliest timestamp across all coins to establish a common time baseline
        earliest_time = None
        for product_id in coins.keys():
            trades = list(ws.MULTI_COIN_TRADES[product_id])
            if trades:
                first_ts = trades[0][0]
                if earliest_time is None or first_ts < earliest_time:
                    earliest_time = first_ts
        
        if earliest_time is None:
            return go.Figure().update_layout(template="plotly_dark")
        
        # Plot each coin with time-based x-axis
        for product_id, config in coins.items():
            trades = list(ws.MULTI_COIN_TRADES[product_id])
            
            if not trades:
                continue
            
            # Extract timestamps and prices
            timestamps = [t[0] for t in trades]
            prices = [t[1] for t in trades]
            
            if not prices:
                continue
            
            # Get reference price
            ref_price = ws.COIN_REFERENCE_PRICES.get(product_id, prices[0])
            
            # Normalize prices to percentage change
            normalized = [((p - ref_price) / ref_price) * 100 for p in prices]
            
            # Convert timestamps to seconds from earliest_time
            x_vals = [(ts - earliest_time) for ts in timestamps]
            
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=normalized,
                mode="lines",
                name=config["name"],
                line=dict(color=config["color"], width=2),
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