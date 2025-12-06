# panels/panel_7.py
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import time
import data.ws_client as ws


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div("Micro-Momentum: Price Displacement per Trade", className="panel-title"),
            dcc.Graph(
                id="panel7-micro",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panel7-interval", interval=300, n_intervals=0)
        ]
    )


def register_callbacks(app):

    @app.callback(
        Output("panel7-micro", "figure"),
        Input("panel7-interval", "n_intervals")
    )
    def update(_):

        if not ws.PRICE_DISPLACEMENT:
            return go.Figure().update_layout(template="plotly_dark")

        # Extract time + displacement
        timestamps = [t for t, dp in ws.PRICE_DISPLACEMENT]
        displacement = [dp for t, dp in ws.PRICE_DISPLACEMENT]

        # Momentum color coding
        colors = ["green" if dp > 0 else "red" for dp in displacement]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=list(range(len(displacement))),
            y=displacement,
            mode="lines+markers",
            marker=dict(size=4, color=colors),
            line=dict(width=1, color="white"),
            name="ΔPrice per trade"
        ))

        # Zero line reference
        fig.add_hline(y=0, line=dict(color="gray", width=1, dash="dot"))

        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=60, r=40, t=60, b=40),
            xaxis_title="Most Recent Trades",
            yaxis_title="Δ Price per Trade",
            showlegend=False
        )

        return fig
