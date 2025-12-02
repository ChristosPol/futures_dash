import plotly.graph_objects as go
from dash import html, dcc
from data.rest_client import get_ohlc
from data.indicators import add_all_smas


def make_figure():
    df = get_ohlc(pair="SOLUSD", interval=1440)
    df = add_all_smas(df)

    fig = go.Figure()

    # Closing price
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["close"],
        name="Close"
    ))

    # SMAs
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["SMA20"],
        name="SMA 20"
    ))
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["SMA50"],
        name="SMA 50"
    ))
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["SMA200"],
        name="SMA 200"
    ))

    # 🔥 minimal layout, EVERYTHING inherited from plotly_dark
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, t=20, b=10),
    )

    return fig


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                "BTC/USD SMA Chart",
                className="panel-title"
            ),

            html.Div(
                dcc.Graph(
                    id="panel1-graph",
                    figure=make_figure(),
                    config={"displayModeBar": False},
                    style={"width": "100%", "height": "100%"}
                ),
                className="panel-graph"
            )
        ]
    )
