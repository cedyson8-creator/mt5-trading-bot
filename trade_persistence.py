import csv
import json
import os


def serialize_features(features):
    if not features:
        return ""
    try:
        return json.dumps(features, default=str)
    except Exception:
        return ""


def deserialize_features(raw):
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_trade_journal(path):
    if not path or not os.path.isfile(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def extract_closed_ids(journal_rows):
    closed = set()
    for row in journal_rows or []:
        status = (row.get("status") or "").upper()
        ticket = str(row.get("ticket") or "").strip()
        if status == "CLOSE" and ticket:
            closed.add(ticket)
    return closed


def write_open_trades_snapshot(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, default=str)


def build_snapshot_row(trade_id, entry, pos):
    return {
        "trade_id": str(trade_id),
        "signal": entry.get("signal"),
        "pair": entry.get("pair"),
        "price": entry.get("price"),
        "sl": entry.get("sl"),
        "tp": entry.get("tp"),
        "lots": entry.get("lots"),
        "entry_time": entry.get("entry_time"),
        "tracked": True,
        "live_position": bool(pos),
        "position_volume": getattr(pos, "volume", None) if pos else None,
        "position_profit": getattr(pos, "profit", None) if pos else None,
    }
