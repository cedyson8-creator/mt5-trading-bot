import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score
from config import (
    ML_MODEL_FILE, ML_LOOKAHEAD, ML_PROFIT_THRESHOLD,
    ML_MIN_SAMPLES, ML_CONFIDENCE_THRESHOLD, ATR_PERIOD,
    ML_FEEDBACK_FILE, ML_MAX_FEEDBACK,
)
from logger import get_logger


def _sma(data, period):
    return pd.Series(data).rolling(window=period).mean().values


def _ema(data, period):
    return pd.Series(data).ewm(span=period, adjust=False).mean().values


def _rsi(data, period=14):
    series = pd.Series(data)
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).values


def _atr(highs, lows, closes, period=14):
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1]),
        ),
    )
    return np.concatenate([[np.nan], pd.Series(tr).rolling(window=period).mean().values])


def _macd(closes):
    ema_12 = _ema(closes, 12)
    ema_26 = _ema(closes, 26)
    macd_line = ema_12 - ema_26
    signal_line = _ema(macd_line, 9)
    return macd_line, signal_line, macd_line - signal_line


def build_feature_matrix(rates):
    closes = np.array([r[4] for r in rates], dtype=float)
    highs = np.array([r[2] for r in rates], dtype=float)
    lows = np.array([r[3] for r in rates], dtype=float)
    n = len(closes)

    # Pre-compute all indicator arrays (vectorized)
    atr_vals = _atr(highs, lows, closes, ATR_PERIOD)
    rsi_vals = _rsi(closes, 14)

    sma_5 = _sma(closes, 5)
    sma_10 = _sma(closes, 10)
    sma_20 = _sma(closes, 20)
    sma_50 = _sma(closes, 50)
    sma_100 = _sma(closes, 100)
    sma_200 = _sma(closes, 200)

    macd_line, macd_signal, macd_hist = _macd(closes)

    bb_std = pd.Series(closes).rolling(20).std().values
    bb_upper = sma_20 + 2 * bb_std
    bb_lower = sma_20 - 2 * bb_std
    bb_width = bb_upper - bb_lower
    bb_position = np.where(bb_width != 0, (closes - bb_lower) / bb_width, 0.5)

    # Pre-compute labels (vectorized)
    labels = []
    for i in range(n):
        if i + ML_LOOKAHEAD >= n:
            labels.append(None)
            continue
        current_atr = atr_vals[i]
        if np.isnan(current_atr):
            labels.append(None)
            continue
        entry = closes[i]
        threshold = current_atr * ML_PROFIT_THRESHOLD
        future_high = np.max(highs[i : i + ML_LOOKAHEAD])
        future_low = np.min(lows[i : i + ML_LOOKAHEAD])
        if future_high >= entry + threshold:
            labels.append("buy")
        elif future_low <= entry - threshold:
            labels.append("sell")
        else:
            labels.append("hold")

    # Build rows at each position (vectorized slice)
    rows = []
    out_labels = []
    min_bars = 200
    total_rows = n - ML_LOOKAHEAD - min_bars
    log = get_logger()

    for idx, i in enumerate(range(min_bars, n - ML_LOOKAHEAD)):
        if idx > 0 and idx % 5000 == 0:
            log.info(f"  Feature progress: {idx}/{total_rows}")
        label = labels[i]
        if label is None:
            continue

        row = {
            "price": closes[i],
            "high": highs[i],
            "low": lows[i],
            "sma_5": sma_5[i],
            "sma_10": sma_10[i],
            "sma_20": sma_20[i],
            "sma_50": sma_50[i],
            "sma_100": sma_100[i],
            "sma_200": sma_200[i],
            "price_sma_5": closes[i] / sma_5[i] if sma_5[i] else 1,
            "price_sma_10": closes[i] / sma_10[i] if sma_10[i] else 1,
            "price_sma_20": closes[i] / sma_20[i] if sma_20[i] else 1,
            "price_sma_50": closes[i] / sma_50[i] if sma_50[i] else 1,
            "price_sma_100": closes[i] / sma_100[i] if sma_100[i] else 1,
            "price_sma_200": closes[i] / sma_200[i] if sma_200[i] else 1,
            "sma_20_50_ratio": sma_20[i] / sma_50[i] if sma_50[i] else 1,
            "sma_50_100_ratio": sma_50[i] / sma_100[i] if sma_100[i] else 1,
            "sma_20_50_cross": 1 if sma_20[i] > sma_50[i] else 0,
            "sma_50_100_cross": 1 if sma_50[i] > sma_100[i] else 0,
            "rsi": rsi_vals[i],
            "rsi_oversold": 1 if rsi_vals[i] < 30 else 0,
            "rsi_overbought": 1 if rsi_vals[i] > 70 else 0,
            "macd": macd_line[i],
            "macd_signal": macd_signal[i],
            "macd_histogram": macd_hist[i],
            "macd_cross": 1 if macd_line[i] > macd_signal[i] else 0,
            "bb_upper": bb_upper[i],
            "bb_lower": bb_lower[i],
            "bb_width": bb_width[i],
            "bb_position": bb_position[i],
            "atr": atr_vals[i],
            "atr_pct": atr_vals[i] / closes[i] if closes[i] else 0,
        }

        for p in [1, 3, 5, 10, 20]:
            if i >= p:
                pct = ((closes[i] - closes[i - p]) / closes[i - p]) * 100
                row[f"change_{p}"] = pct
                window = closes[i - p : i + 1]
                row[f"volatility_{p}"] = np.std(window) / np.mean(window) if np.mean(window) else 0

            row["hl_range"] = (highs[i] - lows[i]) / closes[i] if closes[i] else 0
        if i >= 4:
            row["hl_range_5"] = (np.max(highs[i-4:i+1]) - np.min(lows[i-4:i+1])) / np.mean(closes[i-4:i+1]) if np.mean(closes[i-4:i+1]) else 0

        rows.append(row)
        out_labels.append(label)

    return pd.DataFrame(rows), out_labels


def extract_features(rates):
    closes = np.array([r[4] for r in rates], dtype=float)
    highs = np.array([r[2] for r in rates], dtype=float)
    lows = np.array([r[3] for r in rates], dtype=float)

    atr_vals = _atr(highs, lows, closes, ATR_PERIOD)
    rsi_vals = _rsi(closes, 14)

    sma_5 = _sma(closes, 5)
    sma_10 = _sma(closes, 10)
    sma_20 = _sma(closes, 20)
    sma_50 = _sma(closes, 50)
    sma_100 = _sma(closes, 100)
    sma_200 = _sma(closes, 200)

    macd_line, macd_signal, macd_hist = _macd(closes)

    bb_std = pd.Series(closes).rolling(20).std().values
    bb_upper = sma_20 + 2 * bb_std
    bb_lower = sma_20 - 2 * bb_std
    bb_width = bb_upper - bb_lower
    bb_pos = np.where(bb_width != 0, (closes - bb_lower) / bb_width, 0.5)

    i = -1
    features = {
        "price": closes[i],
        "high": highs[i],
        "low": lows[i],
        "sma_5": sma_5[i],
        "sma_10": sma_10[i],
        "sma_20": sma_20[i],
        "sma_50": sma_50[i],
        "sma_100": sma_100[i],
        "sma_200": sma_200[i],
        "price_sma_5": closes[i] / sma_5[i] if sma_5[i] else 1,
        "price_sma_10": closes[i] / sma_10[i] if sma_10[i] else 1,
        "price_sma_20": closes[i] / sma_20[i] if sma_20[i] else 1,
        "price_sma_50": closes[i] / sma_50[i] if sma_50[i] else 1,
        "price_sma_100": closes[i] / sma_100[i] if sma_100[i] else 1,
        "price_sma_200": closes[i] / sma_200[i] if sma_200[i] else 1,
        "sma_20_50_ratio": sma_20[i] / sma_50[i] if sma_50[i] else 1,
        "sma_50_100_ratio": sma_50[i] / sma_100[i] if sma_100[i] else 1,
        "sma_20_50_cross": 1 if sma_20[i] > sma_50[i] else 0,
        "sma_50_100_cross": 1 if sma_50[i] > sma_100[i] else 0,
        "rsi": rsi_vals[i],
        "rsi_oversold": 1 if rsi_vals[i] < 30 else 0,
        "rsi_overbought": 1 if rsi_vals[i] > 70 else 0,
        "macd": macd_line[i],
        "macd_signal": macd_signal[i],
        "macd_histogram": macd_hist[i],
        "macd_cross": 1 if macd_line[i] > macd_signal[i] else 0,
        "bb_upper": bb_upper[i],
        "bb_lower": bb_lower[i],
        "bb_width": bb_width[i],
        "bb_position": bb_pos[i],
        "atr": atr_vals[i],
        "atr_pct": atr_vals[i] / closes[i] if closes[i] else 0,
    }

    for p in [1, 3, 5, 10, 20]:
        if len(closes) > p:
            pct = ((closes[-1] - closes[-(p+1)]) / closes[-(p+1)]) * 100
            features[f"change_{p}"] = pct
            window = closes[-p-1:]
            features[f"volatility_{p}"] = np.std(window) / np.mean(window) if np.mean(window) else 0

    features["hl_range"] = (highs[-1] - lows[-1]) / closes[-1] if closes[-1] else 0
    if len(closes) >= 5:
        features["hl_range_5"] = (np.max(highs[-5:]) - np.min(lows[-5:])) / np.mean(closes[-5:]) if np.mean(closes[-5:]) else 0

    return features


class MLTradingModel:
    def __init__(self):
        self.logger = get_logger()
        self.model = None
        self.label_encoder = {"buy": 0, "hold": 1, "sell": 2}
        self.reverse_encoder = {0: "buy", 1: "hold", 2: "sell"}
        self.trained = False
        self.training_accuracy = 0
        self.feature_names = None
        self.feedback_buffer = []
        self.open_trades = {}
        self._load_feedback()

    def record_open_trade(self, trade_id, features, signal):
        self.open_trades[trade_id] = {"features": features, "signal": signal}

    def close_trade(self, trade_id, profit):
        if trade_id not in self.open_trades:
            return
        entry = self.open_trades.pop(trade_id)
        entry_signal = entry["signal"]
        features = entry["features"]

        if profit > 0:
            feedback_label = entry_signal
        else:
            feedback_label = "sell" if entry_signal == "buy" else "buy"

        self.feedback_buffer.append((features, feedback_label))
        if len(self.feedback_buffer) > ML_MAX_FEEDBACK:
            self.feedback_buffer = self.feedback_buffer[-ML_MAX_FEEDBACK:]
        self._save_feedback()
        self.logger.info(f"ML feedback: {entry_signal} -> {feedback_label} (profit: ${profit:.2f})")

    def feedback_count(self):
        return len(self.feedback_buffer)

    def _load_feedback(self):
        import pickle
        if os.path.exists(ML_FEEDBACK_FILE):
            try:
                with open(ML_FEEDBACK_FILE, "rb") as f:
                    self.feedback_buffer = pickle.load(f)
                self.logger.info(f"Loaded {len(self.feedback_buffer)} feedback samples")
            except Exception:
                self.feedback_buffer = []

    def _save_feedback(self):
        import pickle
        try:
            with open(ML_FEEDBACK_FILE, "wb") as f:
                pickle.dump(self.feedback_buffer, f)
        except Exception as e:
            self.logger.error(f"Failed to save feedback: {e}")

    def train_with_feedback(self, rates):
        self.logger.info("Building ML feature matrix (with feedback)...")
        X, y = build_feature_matrix(rates)

        if len(X) < ML_MIN_SAMPLES:
            self.logger.warning(f"Not enough samples ({len(X)} < {ML_MIN_SAMPLES}), skipping")
            return False

        self.feature_names = list(X.columns)

        if self.feedback_buffer:
            fb_features = [fb[0] for fb in self.feedback_buffer]
            fb_labels = [fb[1] for fb in self.feedback_buffer]
            fb_df = pd.DataFrame(fb_features)
            fb_df = fb_df.reindex(columns=X.columns, fill_value=0)
            X = pd.concat([X, fb_df], ignore_index=True)
            y = y + fb_labels
            self.logger.info(f"Added {len(fb_labels)} feedback samples ({fb_labels.count('buy')} buy, {fb_labels.count('sell')} sell)")

        y_encoded = [self.label_encoder.get(label, 1) for label in y]

        self.logger.info(f"Training ML model on {len(X)} total samples...")
        self.logger.info(f"Distribution: buy={y.count('buy')} hold={y.count('hold')} sell={y.count('sell')}")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )

        self.model = RandomForestClassifier(
            n_estimators=200, max_depth=15, min_samples_leaf=10,
            random_state=42, n_jobs=-1, class_weight="balanced",
        )
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
        self.training_accuracy = acc
        self.trained = True

        self.logger.info(f"ML trained — Accuracy: {acc:.2%}, Precision: {prec:.2%}")
        self.save()
        return True

    def predict(self, rates):
        if not self.trained or self.model is None:
            return "hold", 0.0

        feats = extract_features(rates)
        df = pd.DataFrame([feats])

        probs = self.model.predict_proba(df)[0]
        pred_class = int(np.argmax(probs))
        confidence = float(probs[pred_class])
        signal = self.reverse_encoder.get(pred_class, "hold")

        if confidence < ML_CONFIDENCE_THRESHOLD:
            return "hold", confidence

        return signal, confidence

    def get_feature_importance(self):
        if self.model is None:
            return {}
        importances = zip(self.model.feature_names_in_, self.model.feature_importances_)
        return dict(sorted(importances, key=lambda x: x[1], reverse=True))

    def save(self):
        import joblib
        joblib.dump({"model": self.model, "accuracy": self.training_accuracy}, ML_MODEL_FILE)
        self._save_feedback()
        self.logger.info(f"ML model saved to {ML_MODEL_FILE}")

    def load(self):
        import joblib
        if not os.path.exists(ML_MODEL_FILE):
            self.logger.info("No saved ML model found")
            return False
        data = joblib.load(ML_MODEL_FILE)
        self.model = data["model"]
        self.training_accuracy = data.get("accuracy", 0)
        self.trained = True
        self.logger.info(f"ML model loaded (accuracy: {self.training_accuracy:.2%})")
        return True
