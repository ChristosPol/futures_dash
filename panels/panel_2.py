# panels/panel_2.py
from dash import html, dcc, Input, Output
from data.metrics_engine import get_hourly_metrics
import plotly.graph_objects as go
import datetime


def layout():
    return html.Div(
        [
            html.H3("Buy/Sell Volume per Hour (Last 24h) — PF_SOLUSD"),
            dcc.Graph(
                id="panel2-bars",
                config={"displayModeBar": False},
                style={"height": "350px"}
            ),
            dcc.Interval(id="panel2-interval", interval=2000, n_intervals=0)
        ],
        className="panel"
    )


def register_callbacks(app):

    @app.callback(
        Output("panel2-bars", "figure"),
        Input("panel2-interval", "n_intervals")
    )
    def update_volume(_):
        metrics = get_hourly_metrics()

        if not metrics:
            fig = go.Figure()
            fig.update_layout(
                template="plotly_dark",
                title="Waiting for data..."
            )
            return fig

        hours = list(metrics.keys())
        buys = []
        sells = []
        totals = []

        for h in hours:
            m = metrics[h]
            b = m["buy_volume"]
            s = m["sell_volume"]
            buys.append(b)
            sells.append(s)
            totals.append(b + s)

        labels = [
            datetime.datetime.fromtimestamp(h).strftime("%H:%M")
            for h in hours
        ]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=labels,
            y=buys,
            name="Buys",
            marker_color="green"
        ))

        fig.add_trace(go.Bar(
            x=labels,
            y=sells,
            name="Sells",
            marker_color="red"
        ))

        # Add totals on top
        for i, total in enumerate(totals):
            fig.add_annotation(
                x=labels[i],
                y=total,
                text=str(round(total, 2)),
                showarrow=False,
                yshift=10,
                font=dict(color="white", size=11)
            )

        fig.update_layout(
            barmode="stack",
            template="plotly_dark",
            margin=dict(l=40, r=20, t=40, b=40),
            xaxis_title="Hour",
            yaxis_title="Volume",
        )

        return fig
