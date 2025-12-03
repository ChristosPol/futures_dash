# panels/panel_3.py
import plotly.graph_objects as go
from dash import html, dcc, Input, Output

import data.ws_client as ws

MAX_BUCKETS_AROUND = 10


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
            dcc.Interval(id="panel3-interval", interval=2000, n_intervals=0)
        ]
    )


def register_callbacks(app):

    @app.callback(
        Output("panel3-histogram", "figure"),
        Input("panel3-interval", "n_intervals")
    )
    def update_hist(_):

        if not ws.PRICE_BUCKETS:
            return go.Figure().update_layout(template="plotly_dark")

        # Determine bucket window
        center = ws.LAST_PRICE or sorted(ws.PRICE_BUCKETS.keys())[0]
        all_buckets = sorted(ws.PRICE_BUCKETS.keys())
        min_b = center - MAX_BUCKETS_AROUND * ws.BUCKET_SIZE
        max_b = center + MAX_BUCKETS_AROUND * ws.BUCKET_SIZE
        buckets = [b for b in all_buckets if min_b <= b <= max_b]

        buy_vol = [ws.PRICE_BUCKETS[b]["buy"] for b in buckets]
        sell_vol = [ws.PRICE_BUCKETS[b]["sell"] for b in buckets]
        labels = [f"{b:.2f}" for b in buckets]

        fig = go.Figure()

        # =========================================================
        # 🔥 Neon Glow Pulse Layer
        # =========================================================
        if ws.FLASH_BUCKET in buckets:
            idx = buckets.index(ws.FLASH_BUCKET)
            pulse_alpha = ws.FLASH_STRENGTH
            ws.FLASH_STRENGTH *= ws.FLASH_DECAY

            if pulse_alpha > 0.05:
                fig.add_shape(
                    type="rect",
                    x0=-max(sell_vol) * 1.2,
                    x1=max(buy_vol) * 1.2,
                    y0=idx - 0.5,
                    y1=idx + 0.5,
                    line=dict(
                        color=f"rgba(0,200,255,{pulse_alpha})",
                        width=8
                    ),
                    layer="below"
                )

        # =========================================================
        # 📊 BUY bars (inside text)
        # =========================================================
        fig.add_trace(go.Bar(
            y=labels,
            x=buy_vol,
            name="Buys",
            marker_color="green",
            orientation="h",
            text=[f"{v:.2f}" for v in buy_vol],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=14),
        ))

        # =========================================================
        # 📊 SELL bars (inside text)
        # =========================================================
        fig.add_trace(go.Bar(
            y=labels,
            x=[-v for v in sell_vol],
            name="Sells",
            marker_color="red",
            orientation="h",
            text=[f"{v:.2f}" for v in sell_vol],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=14),
        ))

        # =========================================================
        # Layout
        # =========================================================
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=80, r=40, t=40, b=40),
            barmode="relative",
            xaxis_title="Volume",
            yaxis_title=f"Buckets (size = {ws.BUCKET_SIZE})",
            showlegend=True,
        )

        # =========================================================
        # 💬 Current Price Annotation
        # =========================================================
        if ws.LAST_PRICE:
            fig.add_annotation(
                text=f"Price {ws.LAST_PRICE:.2f}",
                xref="paper", yref="paper",
                x=0.98,
                y=1.05,
                showarrow=False,
                font=dict(size=14, color="deepskyblue", family="Arial"),
                align="right"
            )

        return fig
