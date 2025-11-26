from dash.dependencies import Input, Output
from panels import panel_1
from data.data_manager import get_latest_data

def register_callbacks(app):

    @app.callback(
        Output("temp_plot", "figure"),
        Input("interval-component", "n_intervals")
    )
    def update_temp_plot(_):
        data = get_latest_data("temperature")
        return panel_1.make_figure(data)