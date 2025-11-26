import plotly.graph_objects as go
from dash import html, dcc

def layout():
    return html.Div([
        html.H1("Panel 6")
    ])
'''
def make_figure(data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["time"], y=data["temp"]))
    return fig
    '''