# panels/panel_9.py

import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import data.ws_client as ws
from datetime import datetime


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div("Hourly Volume Footprint — PF_SOLUSD", className="panel-title"),
            dcc.Graph(
                id="panel9-footprint",
                config={"displayModeBar": False},
                style={"width": "100%", "height": "100%"}
            ),
            dcc.Interval(id="panel9-interval", interval=5000, n_intervals=0)
        ]
    )


def register_callbacks(app):

    @app.callback(
        Output("panel9-footprint", "figure"),
        Input("panel9-interval", "n_intervals")
    )
    def update(_):

        # Get last 10 hours
        hours = sorted(ws.HOURLY_FLOW.keys())[-10:]
        if not hours:
            return go.Figure().update_layout(template="plotly_dark", title="Waiting for data...")

        fig = go.Figure()
        
        # Track all shapes and annotations
        shapes = []
        annotations = []
        
        # Get global min/max prices across all hours for consistent Y-axis
        global_min_price = float('inf')
        global_max_price = float('-inf')
        
        for hour_ts in hours:
            hour_data = ws.HOURLY_FLOW[hour_ts]
            price_levels = hour_data.get("price_levels", {})
            if price_levels:
                prices = list(price_levels.keys())
                global_min_price = min(global_min_price, min(prices))
                global_max_price = max(global_max_price, max(prices))
        
        if global_min_price == float('inf'):
            return go.Figure().update_layout(template="plotly_dark", title="No data yet...")
        
        # Add some padding
        price_range = global_max_price - global_min_price
        global_min_price -= price_range * 0.1
        global_max_price += price_range * 0.1
        
        # Process each hour as a separate candle
        candle_width = 0.8  # Width of each candle
        
        for hour_idx, hour_ts in enumerate(hours):
            hour_data = ws.HOURLY_FLOW[hour_ts]
            hour_label = datetime.fromtimestamp(hour_ts).strftime("%H:%M")
            price_levels = hour_data.get("price_levels", {})
            
            if not price_levels:
                continue
            
            # Sort prices
            sorted_prices = sorted(price_levels.keys())
            
            # Calculate max volume for this hour (for scaling)
            max_vol = 0
            for price in sorted_prices:
                buy_vol = price_levels[price]["buy"]
                sell_vol = price_levels[price]["sell"]
                max_vol = max(max_vol, buy_vol, sell_vol)
            
            if max_vol == 0:
                max_vol = 1
            
            # Bar width scaling factor (max bar extends 0.35 units from center)
            bar_scale = 0.35 / max_vol
            
            # X-center for this candle
            x_center = hour_idx
            
            # Draw bars for each price level
            for price in sorted_prices:
                buy_vol = price_levels[price]["buy"]
                sell_vol = price_levels[price]["sell"]
                
                # Calculate bar widths
                buy_width = buy_vol * bar_scale
                sell_width = sell_vol * bar_scale
                
                # Height of each price bar
                bar_height = 0.15
                
                # Draw sell bar (left, red/orange)
                if sell_vol > 0:
                    # Determine color based on volume magnitude
                    if sell_vol > max_vol * 0.7:
                        color = 'rgba(200, 100, 0, 0.9)'  # Dark orange
                    elif sell_vol > max_vol * 0.3:
                        color = 'rgba(255, 150, 150, 0.8)'  # Light red
                    else:
                        color = 'rgba(255, 200, 200, 0.6)'  # Very light red
                    
                    shapes.append(dict(
                        type="rect",
                        x0=x_center - sell_width,
                        x1=x_center,
                        y0=price - bar_height/2,
                        y1=price + bar_height/2,
                        fillcolor=color,
                        line=dict(width=0)
                    ))
                    
                    # Add volume text
                    if sell_vol >= 1:
                        annotations.append(dict(
                            x=x_center - sell_width/2,
                            y=price,
                            text=f"{int(sell_vol)}",
                            showarrow=False,
                            font=dict(size=7, color='white'),
                            xanchor='center',
                            yanchor='middle'
                        ))
                
                # Draw buy bar (right, green)
                if buy_vol > 0:
                    # Determine color based on volume magnitude
                    if buy_vol > max_vol * 0.7:
                        color = 'rgba(0, 150, 0, 0.9)'  # Dark green
                    elif buy_vol > max_vol * 0.3:
                        color = 'rgba(100, 255, 100, 0.8)'  # Light green
                    else:
                        color = 'rgba(150, 255, 150, 0.6)'  # Very light green
                    
                    shapes.append(dict(
                        type="rect",
                        x0=x_center,
                        x1=x_center + buy_width,
                        y0=price - bar_height/2,
                        y1=price + bar_height/2,
                        fillcolor=color,
                        line=dict(width=0)
                    ))
                    
                    # Add volume text
                    if buy_vol >= 1:
                        annotations.append(dict(
                            x=x_center + buy_width/2,
                            y=price,
                            text=f"{int(buy_vol)}",
                            showarrow=False,
                            font=dict(size=7, color='black'),
                            xanchor='center',
                            yanchor='middle'
                        ))
            
            # Add hour label below candle
            annotations.append(dict(
                x=x_center,
                y=global_min_price - price_range * 0.05,
                text=hour_label,
                showarrow=False,
                font=dict(size=10, color='white'),
                xanchor='center',
                yanchor='top'
            ))
            
            # Add vertical separator line between candles
            if hour_idx < len(hours) - 1:
                shapes.append(dict(
                    type="line",
                    x0=hour_idx + 0.5,
                    x1=hour_idx + 0.5,
                    y0=global_min_price,
                    y1=global_max_price,
                    line=dict(color='rgba(255, 255, 255, 0.2)', width=1, dash='dot')
                ))
        
        # Create dummy trace (Plotly requires at least one trace)
        fig.add_trace(go.Scatter(
            x=[0],
            y=[0],
            mode='markers',
            marker=dict(size=0.1, color='rgba(0,0,0,0)'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Update layout
        fig.update_layout(
            template="plotly_dark",
            shapes=shapes,
            annotations=annotations,
            margin=dict(l=80, r=40, t=10, b=50),
            xaxis=dict(
                title="",
                range=[-0.5, len(hours) - 0.5],
                showgrid=False,
                showticklabels=False,
                zeroline=False
            ),
            yaxis=dict(
                title="Price (USD)",
                range=[global_min_price, global_max_price],
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)',
                tickformat='$.2f'
            ),
            plot_bgcolor='black',
            showlegend=False
        )
        
        return fig