from dash import Dash
import layout
from data.ws_client import start_ws_thread
import callbacks

app = Dash(__name__)
app.layout = layout.serve_layout()
callbacks.register_callbacks(app)

# ---- start websocket feed before the server starts
start_ws_thread()

if __name__ == "__main__":
    app.run(debug=True)