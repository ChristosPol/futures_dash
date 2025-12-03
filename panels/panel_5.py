# panels/panel_5.py
from dash import html, dcc, Input, Output
import data.ws_client as ws


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div("Last 10 Trades — Mini Tape", className="panel-title"),
            html.Div(id="panel5-tape", className="tape-list"),
            dcc.Interval(id="panel5-interval", interval=300, n_intervals=0)
        ]
    )


def register_callbacks(app):

    @app.callback(
        Output("panel5-tape", "children"),
        Input("panel5-interval", "n_intervals")
    )
    def update(_):

        rows = []
        trades = list(reversed(ws.LAST_TRADES))  # newest first

        for t in trades:
            color = "lime" if t["side"] == "buy" else "red"

            rows.append(
                html.Div(
                    [
                        html.Span(f"{t['price']:.2f}", style={"color": color, "width": "80px"}),
                        html.Span(f"{t['volume']:.2f}", style={"color": "white", "width": "80px"}),
                        html.Span(t["side"].upper(), style={"color": color, "width": "60px"}),
                    ],
                    style={"display": "flex", "gap": "12px", "fontSize": "16px"}
                )
            )

        return rows
