# panels/panel_4.py

import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import time
import data.ws_client as ws

MAX_POINTS = 400  # number of points to keep


# -------------------------------------------------------
# PANEL LAYOUT
# -------------------------------------------------------
def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                "Cumulative Delta (CVD) — PF_SOLUSD",
                className="panel-title"
            ),
            html.Div(
                dcc.Graph(
                    id="panel4-cvd",
                    config={"displayModeBar": False},
                    style={"width": "100%", "height": "100%"}
                ),
                className="panel-graph"
            ),
            dcc.Interval(id="panel4-interval", interval=1500, n_intervals=0)
        ]
    )


# -------------------------------------------------------
# CALLBACK LOGIC
# -------------------------------------------------------
def register_callbacks(app):

    @app.callback(
        Output("panel4-cvd", "figure"),
        Input("panel4-interval", "n_intervals")
    )
    def update(_):

        # Initialize history structures if missing
        if not hasattr(ws, "CVD_HISTORY"):
            ws.CVD_HISTORY = []
            ws.PRICE_HISTORY = []
            ws.TIME_HISTORY = []

        # Get latest values
        price = ws.LAST_PRICE
        side = ws.LAST_SIDE
        ts = time.time()

        # -------------------------
        # Update CVD value
        # -------------------------
        delta = 0
        if side == "buy":
            delta = 1
        elif side == "sell":
            delta = -1

        last_cvd = ws.CVD_HISTORY[-1] if ws.CVD_HISTORY else 0
        new_cvd = last_cvd + delta
        ws.CVD_HISTORY.append(new_cvd)
        ws.CVD_HISTORY = ws.CVD_HISTORY[-MAX_POINTS:]

        # -------------------------
        # Safe price update
        # -------------------------
        if price is None:
            if ws.PRICE_HISTORY:
                price = ws.PRICE_HISTORY[-1]
            else:
                price = 0.0

        ws.PRICE_HISTORY.append(price)
        ws.PRICE_HISTORY = ws.PRICE_HISTORY[-MAX_POINTS:]

        # -------------------------
        # Time update
        # -------------------------
        ws.TIME_HISTORY.append(ts)
        ws.TIME_HISTORY = ws.TIME_HISTORY[-MAX_POINTS:]

        # -------------------------
        # Convert to relative seconds (clean X-axis)
        # -------------------------
        if len(ws.TIME_HISTORY) > 1:
            t0 = ws.TIME_HISTORY[0]
            x_vals = [t - t0 for t in ws.TIME_HISTORY]
        else:
            x_vals = [0]

        # -----------------------------------------------------
        # DIVERGENCE DETECTION
        # -----------------------------------------------------
        divergence_text = None
        color = "cyan"

        if len(ws.CVD_HISTORY) > 20 and len(ws.PRICE_HISTORY) > 20:

            p_now = ws.PRICE_HISTORY[-1]
            p_prev = ws.PRICE_HISTORY[-20]

            if p_now is not None and p_prev is not None:
                cvd_slope = ws.CVD_HISTORY[-1] - ws.CVD_HISTORY[-20]
                price_slope = p_now - p_prev

                # Bullish Divergence: price ↓, CVD ↑
                if price_slope < 0 and cvd_slope > 0:
                    color = "lime"
                    divergence_text = "Bullish Divergence"

                # Bearish Divergence: price ↑, CVD ↓
                if price_slope > 0 and cvd_slope < 0:
                    color = "red"
                    divergence_text = "Bearish Divergence"

        # -----------------------------------------------------
        # PLOTTING — CVD (left) + PRICE overlay (right)
        # -----------------------------------------------------
        fig = go.Figure()

        # CVD line
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=ws.CVD_HISTORY,
            mode="lines",
            name="CVD",
            line=dict(color=color, width=3)
        ))

        # Price overlay line
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=ws.PRICE_HISTORY,
            mode="lines",
            name="Price",
            line=dict(color="white", width=1.7, dash="dot"),
            yaxis="y2",
        ))

        # Divergence annotation
        if divergence_text:
            fig.add_annotation(
                x=x_vals[-1],
                y=max(ws.CVD_HISTORY),
                text=f"<b>{divergence_text}</b>",
                font=dict(size=28, color=color),
                showarrow=False,
                xanchor="right"
            )

        # -----------------------------------------------------
        # LAYOUT CONFIG
        # -----------------------------------------------------
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=50, r=70, t=50, b=40),
            xaxis_title="Time (s)",
            yaxis_title="CVD",
            showlegend=False,
            yaxis=dict(
                showgrid=True,
                zeroline=True
            ),
            yaxis2=dict(
                overlaying="y",
                side="right",
                title="Price",
                showgrid=False,
                zeroline=False
            ),
        )

        # Clean tick labels (no scientific notation)
        fig.update_xaxes(
            tickformat=",d",
            nticks=8
        )

        return fig
