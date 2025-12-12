# panels/panel_9.py

import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws
from datetime import datetime


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div("Hourly Footprint Candles (Buy/Sell Volume)", className="panel-title"),
            dcc.Graph(
                id="panel9-footprint",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panel9-interval", interval=5000, n_intervals=0)
        ]
    )


def register_callbacks(app):

    @app.callback(
        Output("panel9-footprint", "figure"),
        Input("panel9-interval", "n_intervals")
    )
    def update(_):

        hours = sorted(ws.HOURLY_FLOW.keys())[-24:]
        if not hours:
            return go.Figure()

        times = []
        opens = []
        highs = []
        lows = []
        closes = []
        buy_vols = []
        sell_vols = []
        arrows = []

        # Extract OHLC + volume from ws_client structures
        for h in hours:
            row = ws.HOURLY_FLOW[h]
            o = row["open"]
            c = row["close"]

            times.append(datetime.fromtimestamp(h))
            opens.append(o)
            highs.append(row["high"])
            lows.append(row["low"])
            closes.append(c)
            buy_vols.append(row["buy_vol"])
            sell_vols.append(row["sell_vol"])

            # Arrow direction
            if c > o:
                arrows.append("↑")
            elif c < o:
                arrows.append("↓")
            else:
                arrows.append("→")

        fig = go.Figure()

        # ===================================================
        # 1) OHLC Candles
        # ===================================================
        fig.add_trace(go.Candlestick(
            x=times,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name="Price",
            increasing_line_color="lime",
            decreasing_line_color="red",
            increasing_fillcolor="rgba(0,255,0,0.3)",
            decreasing_fillcolor="rgba(255,0,0,0.3)",
            showlegend=False
        ))

        # ===================================================
        # 2) Volume Footprint Bars (Behind candles)
        # ===================================================

        # Normalize volumes so bars visually fit under candles
        max_vol = max(max(buy_vols), max(sell_vols), 1)

        scaled_buy = [bv / max_vol for bv in buy_vols]
        scaled_sell = [sv / max_vol for sv in sell_vols]

        # Buy footprint (green bar)
        fig.add_trace(go.Bar(
            x=times,
            y=scaled_buy,
            width=0.03,  # narrow so it fits inside candle
            marker_color="rgba(0,255,0,0.6)",
            name="Buy Volume",
            yaxis="y2",
            showlegend=False
        ))

        # Sell footprint (red bar)
        fig.add_trace(go.Bar(
            x=times,
            y=[-v for v in scaled_sell],  # flip downward
            width=0.03,
            marker_color="rgba(255,0,0,0.6)",
            name="Sell Volume",
            yaxis="y2",
            showlegend=False
        ))

        # ===================================================
        # 3) Arrows indicating net direction (above candle)
        # ===================================================
        for i, t in enumerate(times):
            fig.add_annotation(
                x=t,
                y=highs[i] * 1.001,     # barely above the candle high
                text=arrows[i],
                showarrow=False,
                font=dict(size=18, color="white")
            )

        # ===================================================
        # LAYOUT
        # ===================================================
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=60, r=40, t=60, b=40),

            xaxis=dict(
                title="Time (Hourly)",
                rangeslider=dict(visible=False),
            ),

            yaxis=dict(
                title="Price",
                side="right"
            ),

            # Secondary y-axis for footprint bars
            yaxis2=dict(
                overlaying="y",
                visible=False,      # we hide it, footprint bars only
                range=[-1, 1]
            )
        )

        return fig
