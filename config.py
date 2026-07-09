import os
import MetaTrader5 as mt5
from dotenv import load_dotenv

load_dotenv()

# --- Account ---
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "12345678"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "MetaQuotes-Demo")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# --- Trading Pairs ---
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
TIMEFRAME = mt5.TIMEFRAME_M5
TIMEFRAME_STR = "M5"

# --- Strategy ---
STRATEGY = "ml"   # "sma_rsi" or "ml"
SMA_FAST = 50
SMA_SLOW = 200
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# --- Indicator Filters (enable/disable) ---
USE_MACD_FILTER = True
USE_BB_FILTER = False
USE_ADX_FILTER = True

# MACD
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Bollinger Bands
BB_PERIOD = 20
BB_STD = 2.0

# ADX (trend strength)
ADX_PERIOD = 14
ADX_THRESHOLD = 25

# --- Machine Learning ---
ML_MODEL_FILE = "ml_model.pkl"
ML_FEATURES_FILE = "ml_features.csv"
ML_TRAINING_BARS = 5000         # Bars used for training
ML_LOOKAHEAD = 5                # Bars forward to label (25min on M5)
ML_PROFIT_THRESHOLD = 1.5       # ATR multiplier for buy/sell labeling
ML_RETRAIN_INTERVAL_HOURS = 24  # Retrain every N hours
ML_MIN_SAMPLES = 500            # Minimum samples to train
ML_CONFIDENCE_THRESHOLD = 0.6   # Min probability to take a trade

# --- ML Feedback (online learning) ---
ML_FEEDBACK_FILE = "ml_feedback.pkl"
ML_MAX_FEEDBACK = 2000          # Max feedback samples to keep

# --- Risk Management (Conservative) ---
RISK_PER_TRADE = 0.04           # 4% risk per trade
ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 2.0        # SL = 2 * ATR
RR_RATIO = 2.0                 # TP = 2 * risk (2:1 reward:risk)
MAX_SPREAD_PIPS = 30
MAX_DAILY_LOSS_PCT = 50.0       # Stop trading if down 50% in a day
MAX_CONCURRENT_POSITIONS = 10
MAX_POSITIONS_PER_PAIR = 1

# --- Scheduler ---
CHECK_INTERVAL_SECONDS = 60    # Check for new signals every 60s
ML_TRAINING_INTERVAL_SECONDS = 3600  # Retrain when enough new data
HEARTBEAT_INTERVAL_MINUTES = 60

# --- Paths ---
LOG_FILE = "mt5_bot.log"
TRADE_JOURNAL = "trade_journal.csv"
