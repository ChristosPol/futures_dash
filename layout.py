from dash import html
from panels import (
    panel_1, panel_2, panel_3,
    panel_4, panel_5, panel_6,
    panel_7, panel_8, panel_9
)


def serve_layout():
    return html.Div(
        id="grid-container",
        children=[
            html.Div(panel_1.layout(), className="panel p1"),
            html.Div(panel_2.layout(), className="panel p2"),
            html.Div(panel_3.layout(), className="panel p3"),

            html.Div(panel_4.layout(), className="panel p4"),
            html.Div(panel_5.layout(), className="panel p5"),
            html.Div(panel_6.layout(), className="panel p6"),

            html.Div(panel_7.layout(), className="panel p7"),
            html.Div(panel_8.layout(), className="panel p8"),
            html.Div(panel_9.layout(), className="panel p9"),
        ]
    )
