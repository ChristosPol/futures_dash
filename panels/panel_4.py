# panels/panel_X.py (replace X with your choice)
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws
import numpy as np


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div(
                "Volume Profile — PF_SOLUSD",
                className="panel-title"
            ),
            dcc.Graph(
                id="panelX-volume-profile",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panelX-interval", interval=5000, n_intervals=0)
        ]
    )


def register_callbacks(app):

    @app.callback(
        Output("panelX-volume-profile", "figure"),
        Input("panelX-interval", "n_intervals")
    )
    def update_volume_profile(_):
        
        if not ws.PRICE_BUCKETS:
            return go.Figure().update_layout(
                template="plotly_dark",
                title="Waiting for data..."
            )
        
        # Get volume data from price buckets
        buckets = sorted(ws.PRICE_BUCKETS.keys())
        
        # Calculate total volume at each price level
        price_volumes = {}
        for price in buckets:
            buy_vol = ws.PRICE_BUCKETS[price]["buy"]
            sell_vol = ws.PRICE_BUCKETS[price]["sell"]
            total_vol = buy_vol + sell_vol
            price_volumes[price] = {
                "total": total_vol,
                "buy": buy_vol,
                "sell": sell_vol
            }
        
        # Sort by price
        sorted_prices = sorted(price_volumes.keys())
        total_volumes = [price_volumes[p]["total"] for p in sorted_prices]
        buy_volumes = [price_volumes[p]["buy"] for p in sorted_prices]
        sell_volumes = [price_volumes[p]["sell"] for p in sorted_prices]
        
        # Calculate Point of Control (POC)
        poc_idx = np.argmax(total_volumes)
        poc_price = sorted_prices[poc_idx]
        poc_volume = total_volumes[poc_idx]
        
        # Calculate Value Area (70% of total volume)
        total_traded = sum(total_volumes)
        value_area_volume = total_traded * 0.70
        
        # Find Value Area High (VAH) and Value Area Low (VAL)
        # Start from POC and expand until we reach 70% of volume
        accumulated_volume = poc_volume
        val_idx = poc_idx
        vah_idx = poc_idx
        
        while accumulated_volume < value_area_volume:
            # Expand in the direction with more volume
            volume_below = total_volumes[val_idx - 1] if val_idx > 0 else 0
            volume_above = total_volumes[vah_idx + 1] if vah_idx < len(total_volumes) - 1 else 0
            
            if volume_above > volume_below:
                vah_idx += 1
                accumulated_volume += total_volumes[vah_idx]
            elif volume_below > 0:
                val_idx -= 1
                accumulated_volume += total_volumes[val_idx]
            else:
                break
        
        val_price = sorted_prices[val_idx]
        vah_price = sorted_prices[vah_idx]
        
        fig = go.Figure()
        
        # Add buy volume bars (green)
        fig.add_trace(go.Bar(
            y=sorted_prices,
            x=buy_volumes,
            orientation='h',
            name='Buy Volume',
            marker=dict(
                color='rgba(0, 255, 0, 0.6)',
                line=dict(color='rgba(0, 255, 0, 0.8)', width=1)
            ),
            hovertemplate='Price: $%{y:.2f}<br>Buy Vol: %{x:.0f}<extra></extra>'
        ))
        
        # Add sell volume bars (red, stacked)
        fig.add_trace(go.Bar(
            y=sorted_prices,
            x=sell_volumes,
            orientation='h',
            name='Sell Volume',
            marker=dict(
                color='rgba(255, 0, 0, 0.6)',
                line=dict(color='rgba(255, 0, 0, 0.8)', width=1)
            ),
            hovertemplate='Price: $%{y:.2f}<br>Sell Vol: %{x:.0f}<extra></extra>'
        ))
        
        # Add Point of Control (POC) line
        fig.add_shape(
            type="line",
            x0=0,
            x1=max(total_volumes),
            y0=poc_price,
            y1=poc_price,
            line=dict(color="yellow", width=3, dash="solid"),
        )
        
        # Add Value Area High (VAH) line
        fig.add_shape(
            type="line",
            x0=0,
            x1=max(total_volumes) * 0.7,
            y0=vah_price,
            y1=vah_price,
            line=dict(color="cyan", width=2, dash="dash"),
        )
        
        # Add Value Area Low (VAL) line
        fig.add_shape(
            type="line",
            x0=0,
            x1=max(total_volumes) * 0.7,
            y0=val_price,
            y1=val_price,
            line=dict(color="cyan", width=2, dash="dash"),
        )
        
        # Highlight Value Area
        fig.add_shape(
            type="rect",
            x0=0,
            x1=max(total_volumes),
            y0=val_price,
            y1=vah_price,
            fillcolor="rgba(0, 255, 255, 0.1)",
            line=dict(width=0),
            layer="below"
        )
        
        # Add annotations
        fig.add_annotation(
            x=max(total_volumes) * 0.95,
            y=poc_price,
            text=f"POC: ${poc_price:.2f}",
            showarrow=False,
            font=dict(size=10, color="yellow"),
            xanchor="right",
            bgcolor="rgba(0, 0, 0, 0.7)"
        )
        
        fig.add_annotation(
            x=max(total_volumes) * 0.75,
            y=vah_price,
            text=f"VAH: ${vah_price:.2f}",
            showarrow=False,
            font=dict(size=9, color="cyan"),
            xanchor="right",
            bgcolor="rgba(0, 0, 0, 0.7)"
        )
        
        fig.add_annotation(
            x=max(total_volumes) * 0.75,
            y=val_price,
            text=f"VAL: ${val_price:.2f}",
            showarrow=False,
            font=dict(size=9, color="cyan"),
            xanchor="right",
            bgcolor="rgba(0, 0, 0, 0.7)"
        )
        
        # Add current price line
        if ws.LAST_PRICE:
            fig.add_shape(
                type="line",
                x0=0,
                x1=max(total_volumes),
                y0=ws.LAST_PRICE,
                y1=ws.LAST_PRICE,
                line=dict(color="white", width=2, dash="dot"),
            )
            
            fig.add_annotation(
                x=max(total_volumes) * 0.5,
                y=ws.LAST_PRICE,
                text=f"Current: ${ws.LAST_PRICE:.2f}",
                showarrow=True,
                arrowhead=2,
                arrowcolor="white",
                font=dict(size=10, color="white"),
                bgcolor="rgba(0, 0, 0, 0.8)"
            )
        
        fig.update_layout(
            template="plotly_dark",
            barmode='stack',
            margin=dict(l=60, r=100, t=40, b=40),
            xaxis=dict(
                title="Volume",
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)'
            ),
            yaxis=dict(
                title="Price (USD)",
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)',
                tickformat='$.2f'
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='black'
        )
        
        return fig