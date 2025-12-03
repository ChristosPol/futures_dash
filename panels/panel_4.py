# panels/panel_4.py
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div("Cumulative Delta (CVD) — PF_SOLUSD", className="panel-title"),
            dcc.Graph(
                id="panel4-cvd",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panel4-interval", interval=1000, n_intervals=0)
        ]
    )


def register_callbacks(app):

    cvd_history = []
    price_history = []
    WINDOW = 20   # divergence lookback (20 seconds)

    @app.callback(
        Output("panel4-cvd", "figure"),
        Input("panel4-interval", "n_intervals")
    )
    def update(_):

        # Append CVD
        cvd_history.append(ws.CVD)
        if len(cvd_history) > 600:   # keep ~10 minutes
            cvd_history.pop(0)

        # Append price (fallback to last price)
        price_history.append(ws.LAST_PRICE or price_history[-1] if price_history else 0)
        if len(price_history) > 600:
            price_history.pop(0)

        # ------------------------------
        # DIVERGENCE DETECTION
        # ------------------------------
        divergence_type = None
        divergence_color = "deepskyblue"

        if len(cvd_history) > WINDOW and len(price_history) > WINDOW:
            price_slope = price_history[-1] - price_history[-WINDOW]
            cvd_slope   = cvd_history[-1]   - cvd_history[-WINDOW]

            # Bullish divergence → price down, CVD up
            if price_slope < 0 and cvd_slope > 0:
                divergence_type = "Bullish Divergence"
                divergence_color = "lime"

            # Bearish divergence → price up, CVD down
            if price_slope > 0 and cvd_slope < 0:
                divergence_type = "Bearish Divergence"
                divergence_color = "red"

        # ------------------------------
        # BUILD FIGURE
        # ------------------------------
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            y=cvd_history,
            mode="lines",
            line=dict(color=divergence_color, width=3),
            name="CVD"
        ))

        # Add divergence label if detected
        if divergence_type:
            fig.add_annotation(
                text=f"<b>{divergence_type}</b>",
                xref="paper",
                yref="paper",
                x=0.02, y=1.08,
                showarrow=False,
                font=dict(
                    size=18,
                    color=divergence_color,
                    family="Arial"
                )
            )

        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=50, r=40, t=60, b=40),
            xaxis_title="Time (s)",
            yaxis_title="CVD",
        )

        return fig
