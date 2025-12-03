# panels/panel_6.py
import time
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div("Trade Velocity (Trades / Second)", className="panel-title"),
            dcc.Graph(
                id="panel6-velocity",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panel6-interval", interval=1000, n_intervals=0)
        ]
    )


def register_callbacks(app):

    velocity_history = []

    @app.callback(
        Output("panel6-velocity", "figure"),
        Input("panel6-interval", "n_intervals")
    )
    def update(_):

        # keep timestamps only from last second
        now = time.time()
        recent = [ts for ts in ws.TRADE_TIMESTAMPS if ts >= now - 1.0]
        velocity = len(recent)

        velocity_history.append(velocity)
        if len(velocity_history) > 60:
            velocity_history.pop(0)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=velocity_history,
            mode="lines+markers",
            line=dict(color="orange", width=3),
            marker=dict(size=6),
            name="TPS"
        ))

        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=50, r=40, t=60, b=40),
            xaxis_title="Time (s)",
            yaxis_title="Trades/sec",
        )

        return fig
