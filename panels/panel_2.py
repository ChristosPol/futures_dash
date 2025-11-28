# panels/panel_2.py
from dash import html, dcc, Output, Input
from data.ws_client import get_latest

def layout():
    return html.Div(
        [
            html.H3("Live Futures Ticker (Websocket)"),
            html.Div(id="live-ticker"),
            dcc.Interval(id="live-ticker-interval", interval=1000)
        ],
        className="panel",
    )


def register_callbacks(app):

    @app.callback(
        Output("live-ticker", "children"),
        Input("live-ticker-interval", "n_intervals")
    )
    def update_ticker(_):
        data = get_latest("PF_SOLUSD")

        if not data:
            return "Waiting for data…"

        return (
            f"Last: {data.get('last')} | "
            f"Volume: {data.get('volume')} | "
            f"Bid: {data.get('bid')} | "
            f"Ask: {data.get('ask')}"
        )
