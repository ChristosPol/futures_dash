from dash import Dash
import layout
#import callbacks

app = Dash(__name__)
app.layout = layout.serve_layout()
# callbacks.register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)