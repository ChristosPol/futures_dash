import plotly.graph_objects as go
from dash import html, dcc

from data.rest_client import get_ohlc
from data.indicators import add_all_smas


def make_figure():
    df = get_ohlc(pair="XXBTZUSD", interval=60)
    df = add_all_smas(df)

    fig = go.Figure()

    # Closing price
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["close"],
        name="Close", line=dict(color="#4db8ff", width=2)
    ))

    # SMAs
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["SMA20"],
        name="SMA 20", line=dict(color="yellow", width=1.5)
    ))
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["SMA50"],
        name="SMA 50", line=dict(color="cyan", width=1.5)
    ))
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["SMA200"],
        name="SMA 200", line=dict(color="white", width=2)
    ))

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, t=20, b=10),

        # 🔥 Global font
        font=dict(size=18, color="white"),

        xaxis=dict(
            tickfont=dict(size=20),
            title_font=dict(size=22)
        ),
        yaxis=dict(
            tickfont=dict(size=20),
            title_font=dict(size=22)
        ),

        legend=dict(
            font=dict(size=20),
            orientation="h",
            yanchor="bottom",
            y=1.02
        ),

        autosize=True,
        height=None
    )

    return fig



def layout():
    return html.Div(
        [
            html.Div(
                html.H1(
                    "BTC/USD SMA Chart",
                    style={
                        "color": "white",
                        "margin": "0",
                        "fontSize": "20px",
                    }
                ),
                className="panel-title"
            ),

            dcc.Graph(
                id="panel1-graph",
                figure=make_figure(),
                className="panel-graph",
                config={"displayModeBar": False},
            )
        ],

        # 🔥 CRITICAL for proper height behavior
        style={
            "display": "flex",
            "flexDirection": "column",
            "height": "100%",
            "minHeight": 0
        }
    )
