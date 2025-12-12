# panels/panel_3.py
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws

BUCKET_SIZE = ws.BUCKET_SIZE

def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                id="panel3-title",
                className="panel-title"
            ),
            dcc.Graph(
                id="panel3-histogram",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panel3-interval", interval=2000, n_intervals=0)
        ]
    )

def register_callbacks(app):

    @app.callback(
        Output("panel3-histogram", "figure"),
        Output("panel3-title", "children"),
        Input("panel3-interval", "n_intervals")
    )
    def update_hist(_):

        if not ws.PRICE_BUCKETS:
            return go.Figure(), "Waiting for data..."

        # --------------------------------------
        # KEEP ALL BUCKETS (no windowing)
        # --------------------------------------
        buckets = sorted(ws.PRICE_BUCKETS.keys())

        buy_vol = [ws.PRICE_BUCKETS[b]["buy"] for b in buckets]
        sell_vol = [ws.PRICE_BUCKETS[b]["sell"] for b in buckets]
        labels = [f"{b:.2f}" for b in buckets]

        fig = go.Figure()

        # SELL bars (negative)
        fig.add_trace(go.Bar(
            y=labels,
            x=[-v for v in sell_vol],
            orientation="h",
            marker_color="red",
            name="Sells"
        ))

        # BUY bars (positive)
        fig.add_trace(go.Bar(
            y=labels,
            x=buy_vol,
            orientation="h",
            marker_color="green",
            name="Buys"
        ))

        # --------------------------------------
        # FIX X-RANGE SO BARS NEVER DISAPPEAR
        # --------------------------------------
        max_buy = max(buy_vol) if buy_vol else 0
        max_sell = max(sell_vol) if sell_vol else 0

        fig.update_xaxes(range=[-max_sell * 1.2, max_buy * 1.2])

        fig.update_layout(
            template="plotly_dark",
            barmode="relative",
            margin=dict(l=70, r=40, t=40, b=40),
            xaxis_title="Volume",
            yaxis_title=f"Buckets (size = {BUCKET_SIZE})"
        )

        title = f"Live Buy/Sell Volume by Price Bucket (0.50 USD) — PF_SOLUSD — Price {ws.LAST_PRICE:.2f}"

        return fig, title
