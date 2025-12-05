# panels/panel_3.py
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws

MAX_BUCKETS_AROUND = 10
DECAY_FACTOR = 0.98


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                id="panel3-title",
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
            dcc.Interval(id="panel3-interval", interval=1800, n_intervals=0)
        ]
    )


def register_callbacks(app):

    @app.callback(
        Output("panel3-histogram", "figure"),
        Output("panel3-title", "children"),
        Input("panel3-interval", "n_intervals")
    )
    def update_hist(_):

        # ----------------------------------------------------
        # Fade bucket volumes slightly (decay effect)
        # ----------------------------------------------------
        for b in list(ws.PRICE_BUCKETS.keys()):
            ws.PRICE_BUCKETS[b]["buy"] *= DECAY_FACTOR
            ws.PRICE_BUCKETS[b]["sell"] *= DECAY_FACTOR

        if not ws.PRICE_BUCKETS:
            fig = go.Figure().update_layout(template="plotly_dark")
            return fig, "Live Buy/Sell Volume by Price Bucket (0.50 USD)"

        # ----------------------------------------------------
        # Determine visible bucket window around last price
        # ----------------------------------------------------
        center = ws.LAST_PRICE or sorted(ws.PRICE_BUCKETS.keys())[0]
        all_buckets = sorted(ws.PRICE_BUCKETS.keys())

        min_b = center - MAX_BUCKETS_AROUND * ws.BUCKET_SIZE
        max_b = center + MAX_BUCKETS_AROUND * ws.BUCKET_SIZE

        buckets = [b for b in all_buckets if min_b <= b <= max_b]

        buy_vol = [ws.PRICE_BUCKETS[b]["buy"] for b in buckets]
        sell_vol = [ws.PRICE_BUCKETS[b]["sell"] for b in buckets]
        labels = [f"{b:.2f}" for b in buckets]

        # ----------------------------------------------------
        # Build figure
        # ----------------------------------------------------
        fig = go.Figure()

        # For shape boundaries
        max_buy = max(buy_vol) if buy_vol else 1
        max_sell = max(sell_vol) if sell_vol else 1
        min_x = -max_sell * 1.15
        max_x = max_buy * 1.15

        # ----------------------------------------------------
        # TRUE ABSORPTION DETECTION (Option A)
        # ----------------------------------------------------
        absorption_shapes = []

        for i, b in enumerate(buckets):

            buy_v = ws.PRICE_BUCKETS[b]["buy"]
            sell_v = ws.PRICE_BUCKETS[b]["sell"]

            # Noise filter threshold
            thresh = max(buy_v + sell_v, 1) * 0.25

            # --------------------------------------
            # 🟦 BULLISH ABSORPTION
            # Aggressive sellers fail to move price down
            # --------------------------------------
            if sell_v > thresh and ws.LAST_PRICE and ws.LAST_PRICE > b:
                absorption_shapes.append(dict(
                    type="rect",
                    x0=min_x,
                    x1=max_x,
                    y0=i - 0.45,
                    y1=i + 0.45,
                    line=dict(color="rgba(0,140,255,1.0)", width=3),
                    fillcolor="rgba(0,0,0,0)"
                ))

            # --------------------------------------
            # 🟧 BEARISH ABSORPTION
            # Aggressive buyers fail to move price up
            # --------------------------------------
            if buy_v > thresh and ws.LAST_PRICE and ws.LAST_PRICE < b:
                absorption_shapes.append(dict(
                    type="rect",
                    x0=min_x,
                    x1=max_x,
                    y0=i - 0.45,
                    y1=i + 0.45,
                    line=dict(color="rgba(255,140,0,1.0)", width=3),
                    fillcolor="rgba(0,0,0,0)"
                ))

        # Apply absorption shapes
        for shape in absorption_shapes:
            fig.add_shape(shape)

        # ----------------------------------------------------
        # BUY bars
        # ----------------------------------------------------
        fig.add_trace(go.Bar(
            y=labels,
            x=buy_vol,
            name="Buys",
            marker_color="green",
            orientation="h",
            text=[f"{v:,.2f}" for v in buy_vol],
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate="Buy Volume: %{x:,.2f}<extra></extra>"
        ))

        # ----------------------------------------------------
        # SELL bars
        # ----------------------------------------------------
        fig.add_trace(go.Bar(
            y=labels,
            x=[-v for v in sell_vol],
            name="Sells",
            marker_color="red",
            orientation="h",
            text=[f"{v:,.2f}" for v in sell_vol],
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate="Sell Volume: %{x:,.2f}<extra></extra>"
        ))

        # ----------------------------------------------------
        # Layout
        # ----------------------------------------------------
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=60, r=30, t=40, b=40),
            barmode="relative",
            xaxis_title="Volume",
            yaxis_title=f"Buckets (size = {ws.BUCKET_SIZE})",
            xaxis=dict(range=[min_x, max_x]),
            showlegend=False
        )

        # ----------------------------------------------------
        # Title with current price
        # ----------------------------------------------------
        title_text = (
            f"Live Buy/Sell Volume by Price Bucket (0.50 USD) — PF_SOLUSD"
        )
        if ws.LAST_PRICE:
            title_text += f" — Price {ws.LAST_PRICE:.2f}"

        return fig, title_text
