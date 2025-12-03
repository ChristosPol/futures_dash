# panels/panel_3.py
import plotly.graph_objects as go
from dash import html, dcc, Input, Output

import data.ws_client as ws     # <-- IMPORTANT FIX


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                "Live Buy/Sell Volume by Price Bucket (0.50 USD) — PF_SOLUSD",
                className="panel-title"
            ),

            html.Div(
                dcc.Graph(
                    id="panel3-histogram",
                    config={"displayModeBar": False},
                    style={"width": "100%", "height": "100%"}
                ),
                className="panel-graph"
            ),

            dcc.Interval(
                id="panel3-interval",
                interval=2000,
                n_intervals=0
            )
        ]
    )


def register_callbacks(app):

    @app.callback(
        Output("panel3-histogram", "figure"),
        Input("panel3-interval", "n_intervals")
    )
    def update_hist(_):

        if not ws.PRICE_BUCKETS:
            fig = go.Figure()
            fig.update_layout(
                template="plotly_dark",
                title="Waiting for trade data...",
                xaxis={"visible": False},
                yaxis={"visible": False}
            )
            return fig

        buckets = sorted(ws.PRICE_BUCKETS.keys())
        buy_vol = [ws.PRICE_BUCKETS[b]["buy"] for b in buckets]
        sell_vol = [ws.PRICE_BUCKETS[b]["sell"] for b in buckets]
        labels = [f"{b:.2f}" for b in buckets]

        line_widths = [
            (3 if b == ws.LAST_BUCKET else 0)
            for b in buckets
        ]
        line_colors = [
            ("deepskyblue" if b == ws.LAST_BUCKET else "rgba(0,0,0,0)")
            for b in buckets
        ]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=labels,
            x=buy_vol,
            name="Buys",
            marker_color="green",
            orientation="h",
            marker_line_width=line_widths,
            marker_line_color=line_colors,
        ))

        fig.add_trace(go.Bar(
            y=labels,
            x=[-v for v in sell_vol],
            name="Sells",
            marker_color="red",
            orientation="h",
            marker_line_width=line_widths,
            marker_line_color=line_colors,
        ))

        fig.update_layout(
            template="plotly_dark",
            barmode="relative",
            margin=dict(l=60, r=40, t=80, b=40),
            xaxis_title="Volume",
            yaxis_title=f"Price Bucket (size = {ws.BUCKET_SIZE})"
        )

        # --- Current price text ---
        if ws.LAST_PRICE is not None:
            fig.add_annotation(
                text=f"Current Price: <b>{ws.LAST_PRICE:.2f}</b>",
                xref="paper", yref="paper",
                x=1, y=1.15,
                showarrow=False,
                font=dict(size=18, color="deepskyblue")
            )

        return fig
