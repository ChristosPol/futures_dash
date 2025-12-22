# panels/panel_2.py
from dash import html, dcc, Input, Output
import plotly.graph_objects as go
import data.ws_client as ws


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                "Order Book Depth — PF_SOLUSD",
                className="panel-title"
            ),
            html.Div(
                dcc.Graph(
                    id="panel2-orderbook",
                    config={"displayModeBar": False},
                    style={"width": "100%", "height": "100%"}
                ),
                className="panel-graph"
            ),
            dcc.Interval(
                id="panel2-interval",
                interval=500,  # Update every 500ms for real-time feel
                n_intervals=0
            )
        ]
    )


def register_callbacks(app):

    @app.callback(
        Output("panel2-orderbook", "figure"),
        Input("panel2-interval", "n_intervals")
    )
    def update_orderbook(_):
        
        bids = ws.ORDER_BOOK.get("bids", [])
        asks = ws.ORDER_BOOK.get("asks", [])
        
        if not bids or not asks:
            fig = go.Figure()
            fig.update_layout(
                template="plotly_dark",
                title="Waiting for order book data...",
                xaxis={"visible": False},
                yaxis={"visible": False}
            )
            return fig
        
        # Take top 50 levels for visualization
        bids = bids[:50]
        asks = asks[:50]
        
        # Calculate cumulative volumes
        bid_prices = [b[0] for b in bids]
        bid_volumes = [b[1] for b in bids]
        bid_cumulative = []
        cumsum = 0
        for vol in bid_volumes:
            cumsum += vol
            bid_cumulative.append(cumsum)
        
        ask_prices = [a[0] for a in asks]
        ask_volumes = [a[1] for a in asks]
        ask_cumulative = []
        cumsum = 0
        for vol in ask_volumes:
            cumsum += vol
            ask_cumulative.append(cumsum)
        
        # Create figure
        fig = go.Figure()
        
        # Bids (green)
        fig.add_trace(go.Scatter(
            x=bid_prices,
            y=bid_cumulative,
            mode='lines',
            name='Bids',
            fill='tozeroy',
            line=dict(color='rgba(0, 255, 0, 0.8)', width=2),
            fillcolor='rgba(0, 255, 0, 0.3)',
            hovertemplate='<b>BID</b><br>Price: $%{x:.2f}<br>Cumulative: %{y:,.0f}<extra></extra>'
        ))
        
        # Asks (red)
        fig.add_trace(go.Scatter(
            x=ask_prices,
            y=ask_cumulative,
            mode='lines',
            name='Asks',
            fill='tozeroy',
            line=dict(color='rgba(255, 0, 0, 0.8)', width=2),
            fillcolor='rgba(255, 0, 0, 0.3)',
            hovertemplate='<b>ASK</b><br>Price: $%{x:.2f}<br>Cumulative: %{y:,.0f}<extra></extra>'
        ))
        
        # Current price line (mid-market)
        if bid_prices and ask_prices:
            current_price = (bid_prices[0] + ask_prices[0]) / 2
            max_cum_vol = max(
                bid_cumulative[-1] if bid_cumulative else 0,
                ask_cumulative[-1] if ask_cumulative else 0
            )
            
            fig.add_trace(go.Scatter(
                x=[current_price, current_price],
                y=[0, max_cum_vol],
                mode='lines',
                name=f'Mid: ${current_price:.2f}',
                line=dict(color='white', width=2, dash='dash'),
                showlegend=True
            ))
        
        # Layout
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=60, r=40, t=40, b=40),
            xaxis_title="Price (USD)",
            yaxis_title="Cumulative Volume",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode="x unified"
        )
        
        return fig