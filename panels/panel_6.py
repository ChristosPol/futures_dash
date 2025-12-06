# panels/panel_6.py
import time
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div("Buy/Sell Volume Velocity & Trades/sec", className="panel-title"),
            dcc.Graph(
                id="panel6-velocity",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panel6-interval", interval=1000, n_intervals=0)
        ]
    )


def register_callbacks(app):

    buy_history = []
    sell_history = []
    tps_history = []

    @app.callback(
        Output("panel6-velocity", "figure"),
        Input("panel6-interval", "n_intervals")
    )
    def update(_):

        now = time.time()
        one_sec_ago = now - 1.0

        # -----------------------------
        # BUY VOL / SEC
        # -----------------------------
        recent_buys = [vol for ts, vol in ws.BUY_TIMESTAMPS if ts >= one_sec_ago]
        buy_vol_sec = sum(recent_buys)

        # -----------------------------
        # SELL VOL / SEC
        # -----------------------------
        recent_sells = [vol for ts, vol in ws.SELL_TIMESTAMPS if ts >= one_sec_ago]
        sell_vol_sec = sum(recent_sells)

        # -----------------------------
        # TRADES / SEC
        # -----------------------------
        recent_trades = [ts for ts in ws.TRADE_TIMESTAMPS if ts >= one_sec_ago]
        tps = len(recent_trades)

        # History buffers
        buy_history.append(buy_vol_sec)
        sell_history.append(sell_vol_sec)
        tps_history.append(tps)

        if len(buy_history) > 60:
            buy_history.pop(0)
            sell_history.pop(0)
            tps_history.pop(0)

        # -----------------------------
        # PLOTTING
        # -----------------------------
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            y=buy_history,
            mode="lines+markers",
            line=dict(color="lime", width=2),
            marker=dict(size=5),
            name="Buy Vol/sec",
            yaxis="y1"
        ))

        fig.add_trace(go.Scatter(
            y=sell_history,
            mode="lines+markers",
            line=dict(color="red", width=2),
            marker=dict(size=5),
            name="Sell Vol/sec",
            yaxis="y1"
        ))

        fig.add_trace(go.Scatter(
            y=tps_history,
            mode="lines+markers",
            line=dict(color="cyan", width=2, dash="dot"),
            marker=dict(size=4),
            name="Trades/sec",
            yaxis="y2"
        ))

        # -----------------------------
        # AXES — FIXED VERSION
        # -----------------------------
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=60, r=60, t=60, b=40),

            xaxis=dict(title="Last 60 seconds"),

            # LEFT AXIS — volume/sec
            yaxis=dict(
                title=dict(text="Volume/sec", font=dict(color="white")),
                tickfont=dict(color="white"),
            ),

            # RIGHT AXIS — trades/sec
            yaxis2=dict(
                title=dict(text="Trades/sec", font=dict(color="cyan")),
                tickfont=dict(color="cyan"),
                overlaying="y",
                side="right"
            ),

            legend=dict(orientation="h", y=1.15, x=0.05)
        )

        return fig
