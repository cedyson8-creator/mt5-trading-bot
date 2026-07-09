import urllib.request
import urllib.parse
import json
from config import TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from logger import get_logger


def _send_telegram(message):
    if not TELEGRAM_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message[:4096],
            "parse_mode": "HTML",
        }).encode()
        req = urllib.request.Request(url, data=data)
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status == 200
    except Exception as e:
        get_logger().debug(f"Telegram send failed: {e}")
        return False


def notify_trade_open(signal, pair, lots, price, sl, tp):
    emoji = "🟢" if signal == "buy" else "🔴"
    msg = f"{emoji} <b>TRADE OPEN</b> {pair}\n"
    msg += f"  Signal: {signal.upper()}\n"
    msg += f"  Lots: {lots}\n"
    msg += f"  Price: {price}\n"
    msg += f"  SL: {sl} | TP: {tp}"
    _send_telegram(msg)


def notify_trade_close(pair, signal, profit, balance):
    emoji = "✅" if profit > 0 else "❌"
    msg = f"{emoji} <b>TRADE CLOSE</b> {pair}\n"
    msg += f"  Signal: {signal.upper()}\n"
    msg += f"  P&L: ${profit:.2f}\n"
    msg += f"  Balance: ${balance:.2f}"
    _send_telegram(msg)


def notify_heartbeat(balance, equity, profit, open_positions):
    if not TELEGRAM_ENABLED:
        return
    msg = f"⏰ <b>Heartbeat</b>\n"
    msg += f"  Balance: ${balance:.2f}\n"
    msg += f"  Equity: ${equity:.2f}\n"
    msg += f"  P&L: ${profit:.2f}\n"
    msg += f"  Open trades: {open_positions}"
    _send_telegram(msg)


def notify_error(error_msg):
    _send_telegram(f"⚠️ <b>Bot Error</b>\n  {error_msg}")


def notify_startup():
    _send_telegram("🚀 <b>MT5 Bot Started</b>")
