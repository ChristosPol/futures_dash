# panels/panel_2.py
from dash import html, dcc, Input, Output
import plotly.graph_objects as go
from data.metrics_engine import get_hourly_metrics
import datetime


def layout():
    return html.Div(
        [
            html.H3("Buy/Sell Volume per Hour (Last 24h) — PF_SOLUSD"),

            dcc.Graph(
                id="panel2-volume-bars",
                config={"displayModeBar": False},
                style={"height": "350px"}
            ),

            dcc.Interval(
                id="panel2-interval",
                interval=2000,   # update every 2 seconds
                n_intervals=0
            )
        ],
        className="panel"
    )


def register_callbacks(app):

    @app.callback(
        Output("panel2-volume-bars", "figure"),
        Input("panel2-interval", "n_intervals")
    )
    def update_bars(_):
        metrics = get_hourly_metrics()

        if not metrics:
            fig = go.Figure()
            fig.update_layout(
                template="plotly_dark",
                title="Waiting for data...",
                xaxis={"visible": False},
                yaxis={"visible": False}
            )
            return fig

        # ----- Prepare data -----
        hours = list(metrics.keys())
        buys = []
        sells = []
        totals = []
        costs = []

        for h in hours:
            m = metrics[h]
            buy = m["buy_volume"]
            sell = m["sell_volume"]
            total = buy + sell
            cost = m["buy_cost"] + m["sell_cost"]

            buys.append(buy)
            sells.append(sell)
            totals.append(total)
            costs.append(cost)

        hour_labels = [
            datetime.datetime.fromtimestamp(h).strftime("%H:%M")
            for h in hours
        ]

        # ----- Build stacked bars -----
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=hour_labels,
            y=buys,
            name="Buys",
            marker_color="green"
        ))

        fig.add_trace(go.Bar(
            x=hour_labels,
            y=sells,
            name="Sells",
            marker_color="red"
        ))

        # ----- Add TOTAL VOLUME + TOTAL COST annotations -----
        for i, hour in enumerate(hour_labels):
            label = f"{totals[i]:.2f}  ({costs[i]:,.0f})"

            fig.add_annotation(
                x=hour,
                y=totals[i],
                text=label,
                showarrow=False,
                font=dict(color="white", size=11),
                yshift=12
            )

        # ----- Layout -----
        fig.update_layout(
            barmode="stack",
            template="plotly_dark",
            margin=dict(l=30, r=30, t=40, b=40),
            xaxis_title="Hour",
            yaxis_title="Volume",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        return fig
