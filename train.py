import sys
from logger import setup_logger
from mt5_connector import MT5Connector
from ml_model import MLTradingModel
from config import PAIRS, TIMEFRAME, ML_TRAINING_BARS

log = setup_logger()

log.info("MT5 ML Model Trainer")
log.info("=" * 50)

connector = MT5Connector()
if not connector.connect():
    log.error("Failed to connect to MT5")
    sys.exit(1)

log.info("Fetching historical data for training...")
all_rates = []
for pair in PAIRS:
    rates = connector.get_rates(pair, TIMEFRAME, bars=ML_TRAINING_BARS)
    if rates is not None:
        all_rates.extend(rates)
        log.info(f"  {pair}: {len(rates)} bars loaded")
    else:
        log.warning(f"  {pair}: no data")

if len(all_rates) < 500:
    log.error(f"Not enough data ({len(all_rates)} bars)")
    sys.exit(1)

log.info(f"Total bars across all pairs: {len(all_rates)}")

model = MLTradingModel()
model.train_with_feedback(all_rates)

if model.trained:
    log.info("=" * 50)
    log.info("Training complete!")
    log.info(f"  Accuracy: {model.training_accuracy:.2%}")
    log.info(f"  Model saved to: ml_model.pkl")

    importance = model.get_feature_importance()
    if importance:
        log.info("Top 10 features by importance:")
        for name, score in list(importance.items())[:10]:
            log.info(f"  {name}: {score:.4f}")
else:
    log.error("Training failed")

connector.disconnect()
log.info("Done.")
