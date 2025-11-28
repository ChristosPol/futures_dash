# callbacks.py
from panels import panel_2

def register_callbacks(app):
    # Register only panel_2 callbacks (panel_1 uses REST without callbacks)
    panel_2.register_callbacks(app)
