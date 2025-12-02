# layout.py
from dash import html
from panels import panel_1, panel_2, panel_3, panel_4, panel_5, panel_6, panel_7, panel_8, panel_9


def serve_layout():
    return html.Div(
        id="grid-container",
        children=[
            panel_1.layout(),
            panel_2.layout(),
            panel_3.layout(),
            panel_4.layout(),
            panel_5.layout(),
            panel_6.layout(),
            panel_7.layout(),
            panel_8.layout(),
            panel_9.layout(),
        ]
    )
