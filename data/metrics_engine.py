# data/metrics_engine.py
import time
from threading import Lock

# Stores 24 hourly buckets
metrics = {}
lock = Lock()


def _hour(ts):
    """Round unix timestamp to hour."""
    return int(ts // 3600 * 3600)


def add_trade(price, volume, side, ts):
    """Called for each trade from ws_client."""
    hour = _hour(ts)

    with lock:
        if hour not in metrics:
            metrics[hour] = {
                "buy_volume": 0.0,
                "sell_volume": 0.0,
                "buy_cost": 0.0,
                "sell_cost": 0.0,
                "buy_count": 0,
                "sell_count": 0,
                "trade_count": 0
            }

        m = metrics[hour]

        # update metrics
        if side == "buy":
            m["buy_volume"] += volume
            m["buy_cost"] += price * volume
            m["buy_count"] += 1
        else:
            m["sell_volume"] += volume
            m["sell_cost"] += price * volume
            m["sell_count"] += 1

        m["trade_count"] += 1

        cleanup_old()


def cleanup_old():
    """Keep last 24 hours only."""
    cutoff = time.time() - 24 * 3600
    old = [h for h in metrics if h < cutoff]
    for h in old:
        del metrics[h]


def get_hourly_metrics():
    """Returns {hour_timestamp: metrics} sorted by hour."""
    with lock:
        return dict(sorted(metrics.items()))
