# panels/panel_5.py
from dash import html, dcc, Input, Output
import data.ws_client as ws
from datetime import datetime


def layout():
    return html.Div(
        className="panel",
        children=[
            html.Div("Last 20 Trades — Mini Tape", className="panel-title"),
            html.Div(
                id="panel5-tape",
                className="tape-list",
                style={
                    "overflowY": "auto",  # Enable vertical scrolling
                    "height": "100%",      # Take full height
                    "maxHeight": "100%"
                }
            ),
            dcc.Interval(id="panel5-interval", interval=300, n_intervals=0),
            # Audio element for alert sound
            html.Audio(id="alert-sound", src="", autoPlay=False)
        ]
    )


def register_callbacks(app):
    
    last_alert_time = [0]  # Track last alert to avoid spam

    @app.callback(
        Output("panel5-tape", "children"),
        Output("alert-sound", "src"),
        Input("panel5-interval", "n_intervals")
    )
    def update(_):

        rows = []
        trades = list(reversed(ws.LAST_TRADES))[-20:]  # Last 20, newest first
        
        play_alert = False
        current_time = datetime.now().timestamp()

        if not trades:
            return html.Div(
                "Waiting for trades...",
                style={
                    "color": "#666",
                    "fontSize": "16px",
                    "textAlign": "center",
                    "padding": "20px"
                }
            ), ""

        for i, t in enumerate(trades):
            color = "lime" if t["side"] == "buy" else "red"
            bg_color = "rgba(0,255,0,0.1)" if t["side"] == "buy" else "rgba(255,0,0,0.1)"
            
            # Time formatting
            time_str = datetime.fromtimestamp(t["time"]).strftime("%H:%M:%S")
            
            # Calculate trade value
            trade_value = t["price"] * t["volume"]
            is_large_trade = trade_value >= 2000
            
            # Check if we should play alert (only for recent trades, avoid spam)
            if is_large_trade and (current_time - last_alert_time[0]) > 2:
                play_alert = True
                last_alert_time[0] = current_time
            
            # Add alternating background for better readability
            if i % 2 == 0:
                bg_alpha = "0.05"
            else:
                bg_alpha = "0.02"
            
            # Override background for large trades
            if is_large_trade:
                bg_alpha = "0.15"
                bg_color = "rgba(255,215,0,0.2)"  # Gold background for alerts
            
            row_children = [
                html.Span(
                    time_str,
                    style={
                        "color": "#888",
                        "width": "70px",
                        "fontFamily": "monospace",
                        "fontSize": "13px"
                    }
                ),
                html.Span(
                    f"${t['price']:.2f}",
                    style={
                        "color": color,
                        "width": "85px",
                        "fontWeight": "bold",
                        "fontFamily": "monospace",
                        "fontSize": "15px"
                    }
                ),
                html.Span(
                    f"{t['volume']:.2f}",
                    style={
                        "color": "white",
                        "width": "70px",
                        "fontFamily": "monospace",
                        "fontSize": "14px"
                    }
                ),
                html.Span(
                    t["side"].upper(),
                    style={
                        "color": color,
                        "width": "55px",
                        "fontWeight": "bold",
                        "fontSize": "13px",
                        "backgroundColor": bg_color,
                        "padding": "2px 6px",
                        "borderRadius": "3px"
                    }
                ),
            ]
            
            # Add alert badge for large trades
            if is_large_trade:
                row_children.append(
                    html.Span(
                        f"🚨 ${trade_value:,.0f}",
                        style={
                            "color": "#FFD700",
                            "fontWeight": "bold",
                            "fontSize": "14px",
                            "marginLeft": "8px",
                            "animation": "pulse 1s infinite"
                        }
                    )
                )
            
            rows.append(
                html.Div(
                    row_children,
                    style={
                        "display": "flex",
                        "gap": "10px",
                        "padding": "6px 10px",
                        "borderBottom": "1px solid rgba(255,255,255,0.1)",
                        "backgroundColor": f"rgba(255,255,255,{bg_alpha})",
                        "alignItems": "center",
                        "borderLeft": "3px solid gold" if is_large_trade else "3px solid transparent"
                    }
                )
            )

        # Return with or without alert sound
        alert_src = "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBTGH0fPTgjMGHm7A7+OZSA0PVqzn77BdGAg+ltryxnMpBSuAzu/glEILElyx6OyhUBELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhELTKXh8bllHAU2jdXzzn0vBSh+y+7fk0IJE1yw6OyjUhEK" if play_alert else ""

        return rows, alert_src