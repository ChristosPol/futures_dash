from dash import Dash
import layout
from data.ws_client import start_ws_thread
import callbacks
import plotly.io as pio
pio.templates.default = "plotly_dark"

app = Dash(__name__)
app.layout = layout.serve_layout()

# Register app callbacks
callbacks.register_callbacks(app)

# Start websocket listener
start_ws_thread()

if __name__ == "__main__":
    app.run(debug=True)
