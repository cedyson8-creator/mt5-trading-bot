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


def _pip_size(symbol_info):
    # For most FX symbols, one pip is 10 points on 5-digit/3-digit pricing.
    # For everything else, fall back to one point.
    if symbol_info is None:
        return None
    digits = getattr(symbol_info, "digits", 0) or 0
    point = getattr(symbol_info, "point", 0) or 0
    if point <= 0:
        return None
    return point * 10 if digits in (3, 5) else point


def calculate_trailing_sl(position, current_price, atr_value, digits=None):
    entry = position.price_open
    direction = "buy" if position.type == 0 else "sell"
    current_sl = position.sl
    sl_distance = atr_value * TRAILING_SL_DISTANCE

    if direction == "buy":
        profit_distance = current_price - entry
        if profit_distance < atr_value * TRAILING_SL_ACTIVATION:
            return None
        new_sl = round(current_price - sl_distance, digits if digits is not None else 5)
        if current_sl is None or current_sl == 0.0:
            return new_sl
        return new_sl if new_sl > current_sl else None
    else:
        profit_distance = entry - current_price
        if profit_distance < atr_value * TRAILING_SL_ACTIVATION:
            return None
        new_sl = round(current_price + sl_distance, digits if digits is not None else 5)
        if current_sl is None or current_sl == 0.0:
            return new_sl
        return new_sl if new_sl < current_sl else None


def calculate_position_size(account_balance, entry_price, sl_price, symbol_info, pair=""):
    multiplier = get_pair_risk_multiplier(pair)
    risk_amount = account_balance * RISK_PER_TRADE * multiplier

    if symbol_info is None or getattr(symbol_info, "trade_tick_size", 0) in (0, None) or getattr(symbol_info, "trade_tick_value", 0) in (0, None):
        return 0.0

    stop_distance = abs(entry_price - sl_price)
    if stop_distance <= 0:
        return 0.0

    tick_value = float(symbol_info.trade_tick_value)
    tick_size = float(symbol_info.trade_tick_size)
    risk_per_lot = (stop_distance / tick_size) * tick_value
    if risk_per_lot <= 0:
        return 0.0

    raw_lots = risk_amount / risk_per_lot
    step = float(symbol_info.volume_step)
    min_vol = float(symbol_info.volume_min)
    max_vol = float(symbol_info.volume_max)

    if step <= 0 or max_vol <= 0:
        return 0.0

    lots = np.floor(raw_lots / step) * step
    if lots < min_vol:
        return 0.0

    lots = min(lots, max_vol)
    return round(float(lots), 8)


def check_spread(symbol_info):
    pip_size = _pip_size(symbol_info)
    if pip_size is None:
        return False
    spread_price = symbol_info.spread * symbol_info.point
    max_spread_price = MAX_SPREAD_PIPS * pip_size
    return spread_price <= max_spread_price


def check_daily_loss(daily_start_balance, current_equity):
    if daily_start_balance is None or daily_start_balance <= 0:
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


def calculate_sl_tp(rates, entry_price, direction, digits=5):
    atr_val = _atr(rates)
    if atr_val is None:
        return None, None

    sl_distance = atr_val * ATR_SL_MULTIPLIER

    if direction == "buy":
        sl = round(entry_price - sl_distance, digits)
        tp = round(entry_price + sl_distance * RR_RATIO, digits)
    else:
        sl = round(entry_price + sl_distance, digits)
        tp = round(entry_price - sl_distance * RR_RATIO, digits)

    return sl, tp


def get_pair_risk_multiplier(pair):
    if not REBALANCE_ENABLED or not os.path.isfile(TRADE_JOURNAL):
        return 1.0

    trades = []
    try:
        with open(TRADE_JOURNAL, "r") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            profit_idx = header.index("profit") if header and "profit" in header else None
            status_idx = header.index("status") if header and "status" in header else None
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
        if profit_idx is None:
            return 1.0
        if len(t) <= profit_idx:
            continue
        if status_idx is not None and len(t) > status_idx and t[status_idx] and t[status_idx].upper() != "CLOSE":
            continue
        try:
            profit = float(t[profit_idx]) if t[profit_idx] else 0
        except ValueError:
            continue
        if profit > 0:
            wins += 1

    closed_count = sum(
        1 for t in recent
        if (status_idx is None or (len(t) > status_idx and t[status_idx].upper() == "CLOSE"))
        and len(t) > profit_idx
    )
    if closed_count < 3:
        return 1.0

    win_rate = wins / closed_count
    if win_rate >= 0.6:
        return REBALANCE_MAX_RISK_MULT
    elif win_rate <= 0.4:
        return REBALANCE_MIN_RISK_MULT
    return 1.0
