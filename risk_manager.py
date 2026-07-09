import numpy as np
import csv
import os
from config import (
    RISK_PER_TRADE, ATR_PERIOD, ATR_SL_MULTIPLIER, RR_RATIO,
    MAX_SPREAD_PIPS, MAX_DAILY_LOSS_PCT, MAX_CONCURRENT_POSITIONS,
    MAX_POSITIONS_PER_PAIR, DRY_RUN,
    TRAILING_SL_ACTIVATION, TRAILING_SL_DISTANCE,
    REBALANCE_ENABLED, REBALANCE_WINDOW, REBALANCE_MAX_RISK_MULT,
    REBALANCE_MIN_RISK_MULT, TRADE_JOURNAL,
)
from logger import get_logger


def _atr(rates, period=ATR_PERIOD):
    highs = np.array([r[2] for r in rates])
    lows = np.array([r[3] for r in rates])
    closes = np.array([r[4] for r in rates])

    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1]),
        ),
    )
    if len(tr) < period:
        return None
    return np.mean(tr[-period:])


def calculate_trailing_sl(position, current_price, atr_value):
    entry = position.price_open
    direction = "buy" if position.type == 0 else "sell"
    current_sl = position.sl
    sl_distance = atr_value * TRAILING_SL_DISTANCE

    if direction == "buy":
        profit_distance = current_price - entry
        if profit_distance < atr_value * TRAILING_SL_ACTIVATION:
            return None
        new_sl = round(current_price - sl_distance, 5)
        if current_sl is None or current_sl == 0.0:
            return new_sl
        return new_sl if new_sl > current_sl else None
    else:
        profit_distance = entry - current_price
        if profit_distance < atr_value * TRAILING_SL_ACTIVATION:
            return None
        new_sl = round(current_price + sl_distance, 5)
        if current_sl is None or current_sl == 0.0:
            return new_sl
        return new_sl if new_sl < current_sl else None


def calculate_position_size(account_balance, entry_price, sl_price, symbol_info, pair=""):
    multiplier = get_pair_risk_multiplier(pair)
    risk_amount = account_balance * RISK_PER_TRADE * multiplier

    stop_loss_pips = abs(entry_price - sl_price) / symbol_info.point
    if stop_loss_pips <= 0:
        return 0.0

    tick_value = symbol_info.trade_tick_value
    tick_size = symbol_info.trade_tick_size
    pip_value_per_lot = (tick_value / tick_size) * symbol_info.point

    lots = round(risk_amount / (stop_loss_pips * pip_value_per_lot), 2)
    lots = max(symbol_info.volume_min, min(lots, symbol_info.volume_max))
    lots = round(lots / symbol_info.volume_step) * symbol_info.volume_step

    return lots


def check_spread(symbol_info):
    spread_pips = symbol_info.spread * symbol_info.point
    max_spread = MAX_SPREAD_PIPS * symbol_info.point
    return spread_pips <= max_spread


def check_daily_loss(daily_start_balance, current_equity):
    if daily_start_balance <= 0:
        return True
    loss_pct = ((daily_start_balance - current_equity) / daily_start_balance) * 100
    return loss_pct < MAX_DAILY_LOSS_PCT


def check_position_limits(connector, pair):
    positions = connector.get_positions()
    count_all = len(positions) if positions else 0
    count_pair = sum(1 for p in positions if p.symbol == pair) if positions else 0

    if count_all >= MAX_CONCURRENT_POSITIONS:
        return False, f"Max concurrent positions reached ({MAX_CONCURRENT_POSITIONS})"
    if count_pair >= MAX_POSITIONS_PER_PAIR:
        return False, f"Max positions for {pair} reached ({MAX_POSITIONS_PER_PAIR})"
    return True, ""


def calculate_sl_tp(rates, entry_price, direction):
    atr_val = _atr(rates)
    if atr_val is None:
        return None, None

    sl_distance = atr_val * ATR_SL_MULTIPLIER

    if direction == "buy":
        sl = round(entry_price - sl_distance, 5)
        tp = round(entry_price + sl_distance * RR_RATIO, 5)
    else:
        sl = round(entry_price + sl_distance, 5)
        tp = round(entry_price - sl_distance * RR_RATIO, 5)

    return sl, tp


def get_pair_risk_multiplier(pair):
    if not REBALANCE_ENABLED or not os.path.isfile(TRADE_JOURNAL):
        return 1.0

    trades = []
    try:
        with open(TRADE_JOURNAL, "r") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 3 and row[2] == pair:
                    trades.append(row)
    except Exception:
        return 1.0

    recent = trades[-REBALANCE_WINDOW:]
    if len(recent) < 3:
        return 1.0

    wins = 0
    for t in recent:
        action = t[1] if len(t) > 1 else ""
        if action.startswith("LIVE_BUY") or action.startswith("LIVE_SELL") or \
           action.startswith("DRY_BUY") or action.startswith("DRY_SELL"):
            profit = float(t[5]) if len(t) > 5 and t[5] else 0
            if profit > 0:
                wins += 1

    win_rate = wins / len(recent)
    if win_rate >= 0.6:
        return REBALANCE_MAX_RISK_MULT
    elif win_rate <= 0.4:
        return REBALANCE_MIN_RISK_MULT
    return 1.0
