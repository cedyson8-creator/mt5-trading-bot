import pandas as pd
import numpy as np
from config import (
    SMA_FAST, SMA_SLOW, RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD, STRATEGY,
    USE_MACD_FILTER, USE_BB_FILTER, USE_ADX_FILTER,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BB_PERIOD, BB_STD,
    ADX_PERIOD, ADX_THRESHOLD,
)

# Global ML model reference (set at startup)
_ml_model = None

def set_ml_model(model):
    global _ml_model
    _ml_model = model


def _sma(data, period):
    return pd.Series(data).rolling(window=period).mean().values


def _ema(data, period):
    return pd.Series(data).ewm(span=period, adjust=False).mean().values


def _rsi(data, period):
    series = pd.Series(data)
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.values


def _macd(closes):
    ema_fast = _ema(closes, MACD_FAST)
    ema_slow = _ema(closes, MACD_SLOW)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, MACD_SIGNAL)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bollinger_bands(closes):
    middle = _sma(closes, BB_PERIOD)
    std = pd.Series(closes).rolling(window=BB_PERIOD).std().values
    upper = middle + (std * BB_STD)
    lower = middle - (std * BB_STD)
    return upper, middle, lower


def _adx(highs, lows, closes):
    series_h = pd.Series(highs)
    series_l = pd.Series(lows)
    series_c = pd.Series(closes)

    plus_dm = series_h.diff()
    minus_dm = series_l.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = minus_dm.abs()

    tr = pd.concat([series_h - series_l, (series_h - series_c.shift()).abs(), (series_l - series_c.shift()).abs()], axis=1).max(axis=1)

    atr = tr.rolling(window=ADX_PERIOD).mean()
    plus_di = 100 * (plus_dm.rolling(window=ADX_PERIOD).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=ADX_PERIOD).mean() / atr)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    adx = dx.rolling(window=ADX_PERIOD).mean()

    return adx.values, plus_di.values, minus_di.values


def sma_rsi_signal(rates):
    closes = [r[4] for r in rates]
    if len(closes) < SMA_SLOW + 1:
        return "hold"

    sma_fast = _sma(closes, SMA_FAST)
    sma_slow = _sma(closes, SMA_SLOW)
    rsi_vals = _rsi(closes, RSI_PERIOD)

    prev_fast = sma_fast[-2]
    prev_slow = sma_slow[-2]
    curr_fast = sma_fast[-1]
    curr_slow = sma_slow[-1]
    curr_rsi = rsi_vals[-1]

    if np.isnan(curr_rsi) or np.isnan(curr_fast) or np.isnan(curr_slow):
        return "hold"

    if prev_fast <= prev_slow and curr_fast > curr_slow and curr_rsi < RSI_OVERBOUGHT:
        return "buy"

    if prev_fast >= prev_slow and curr_fast < curr_slow and curr_rsi > RSI_OVERSOLD:
        return "sell"

    return "hold"


# --- Indicator Filters ---

def macd_filter(closes, signal_dir):
    if not USE_MACD_FILTER:
        return True

    macd_line, signal_line, hist = _macd(closes)
    curr_macd = macd_line[-1]
    curr_signal = signal_line[-1]
    prev_macd = macd_line[-2]
    prev_signal = signal_line[-2]
    curr_hist = hist[-1]

    if np.isnan(curr_macd) or np.isnan(curr_signal):
        return True

    if signal_dir == "buy":
        return curr_macd > curr_signal
    elif signal_dir == "sell":
        return curr_macd < curr_signal

    return True


def bb_filter(closes, price, signal_dir):
    if not USE_BB_FILTER:
        return True

    upper, middle, lower = _bollinger_bands(closes)
    curr_lower = lower[-1]
    curr_upper = upper[-1]

    if np.isnan(curr_lower) or np.isnan(curr_upper):
        return True

    if signal_dir == "buy":
        return price <= curr_lower
    elif signal_dir == "sell":
        return price >= curr_upper

    return True


def adx_filter(highs, lows, closes, signal_dir):
    if not USE_ADX_FILTER:
        return True

    adx_vals, plus_di, minus_di = _adx(highs, lows, closes)
    curr_adx = adx_vals[-1]
    curr_plus = plus_di[-1]
    curr_minus = minus_di[-1]

    if np.isnan(curr_adx):
        return True

    if curr_adx < ADX_THRESHOLD:
        return False

    if signal_dir == "buy":
        return curr_plus > curr_minus
    elif signal_dir == "sell":
        return curr_minus > curr_plus

    return True


def generate_signal(rates):
    if STRATEGY == "ml":
        if _ml_model is None or not _ml_model.trained:
            return "hold"
        signal, confidence = _ml_model.predict(rates)
        return signal

    if STRATEGY != "sma_rsi":
        return "hold"

    closes = [r[4] for r in rates]
    highs = [r[2] for r in rates]
    lows = [r[3] for r in rates]

    signal = sma_rsi_signal(rates)
    if signal == "hold":
        return "hold"

    all_pass = (
        macd_filter(closes, signal)
        and bb_filter(closes, rates[-1][4], signal)
        and adx_filter(highs, lows, closes, signal)
    )

    return signal if all_pass else "hold"
