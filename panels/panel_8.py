# panels/panel_8.py

import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws
import time
from datetime import datetime


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div("Directional Volume Efficiency (Last 24 Hours)", className="panel-title"),
            dcc.Graph(
                id="panel8-directional",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panel8-interval", interval=5000, n_intervals=0)
        ]
    )


def register_callbacks(app):

    @app.callback(
        Output("panel8-directional", "figure"),
        Input("panel8-interval", "n_intervals")
    )
    def update(_):

        hours = sorted(ws.HOURLY_FLOW.keys())[-24:]
        if not hours:
            return go.Figure()

        labels = []
        buy_vol = []
        sell_vol = []
        arrows = []

        for h in hours:
            row = ws.HOURLY_FLOW[h]

            labels.append(datetime.fromtimestamp(h).strftime("%H:%M"))
            buy_vol.append(row["buy_vol"])
            sell_vol.append(-row["sell_vol"])   # negative for left side

            # REAL PRICE DIRECTION
            open_p = row["open"]
            close_p = row["close"]

            if close_p > open_p:
                arrows.append("↑")
            elif close_p < open_p:
                arrows.append("↓")
            else:
                arrows.append("→")

        fig = go.Figure()

        # Sell (left)
        fig.add_trace(go.Bar(
            y=labels,
            x=sell_vol,
            orientation='h',
            name="Downward Pressure",
            marker_color="red"
        ))

        # Buy (right)
        fig.add_trace(go.Bar(
            y=labels,
            x=buy_vol,
            orientation='h',
            name="Upward Pressure",
            marker_color="green"
        ))

        # Add arrows next to bars
        for i, label in enumerate(labels):
            fig.add_annotation(
                x=0,
                y=label,
                text=arrows[i],
                font=dict(size=22, color="white"),
                showarrow=False,
                xanchor="center"
            )

        fig.update_layout(
            template="plotly_dark",
            barmode="relative",
            xaxis_title="Directional Volume",
            yaxis_title="Hour",
            legend=dict(orientation="h", x=0.5, xanchor="center"),
            margin=dict(l=60, r=40, t=40, b=40),
        )

        return fig
