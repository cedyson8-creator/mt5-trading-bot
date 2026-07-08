import pandas as pd
import numpy as np
from strategy_engine import sma_rsi_signal


def backtest(pair, rates, initial_balance=10000, risk_per_trade=0.01):
    balance = initial_balance
    equity_curve = [balance]
    trades = []

    for i in range(200, len(rates)):
        chunk = rates[i - 200:i + 1]
        signal = sma_rsi_signal(chunk)
        if signal == "hold":
            equity_curve.append(balance)
            continue

        price = rates[i][4]
        atr = np.mean([abs(r[2] - r[3]) for r in chunk[-14:]])
        sl_dist = atr * 2.0
        sl = price - sl_dist if signal == "buy" else price + sl_dist
        tp = price + sl_dist * 2.0 if signal == "buy" else price - sl_dist * 2.0
        risk_amount = balance * risk_per_trade
        lots = round(risk_amount / sl_dist, 2) if sl_dist > 0 else 0
        if lots <= 0:
            equity_curve.append(balance)
            continue

        # Simulate trade result
        if signal == "buy":
            if rates[i + 1][4] >= tp if i + 1 < len(rates) else False:
                profit = risk_amount * 2.0
            elif rates[i + 1][4] <= sl if i + 1 < len(rates) else False:
                profit = -risk_amount
            else:
                exit_price = rates[i + 1][4]
                profit = (exit_price - price) / sl_dist * risk_amount
        else:
            if rates[i + 1][4] <= tp if i + 1 < len(rates) else False:
                profit = risk_amount * 2.0
            elif rates[i + 1][4] >= sl if i + 1 < len(rates) else False:
                profit = -risk_amount
            else:
                exit_price = rates[i + 1][4]
                profit = (price - exit_price) / sl_dist * risk_amount

        balance += profit
        equity_curve.append(balance)
        trades.append({
            "time": rates[i][0],
            "signal": signal,
            "price": price,
            "sl": sl,
            "tp": tp,
            "profit": round(profit, 2),
            "balance": round(balance, 2),
        })

    df = pd.DataFrame(trades)
    total_return = ((balance - initial_balance) / initial_balance) * 100
    win_rate = (df["profit"] > 0).mean() * 100 if len(df) > 0 else 0

    return {
        "pair": pair,
        "initial_balance": initial_balance,
        "final_balance": round(balance, 2),
        "total_return_pct": round(total_return, 2),
        "total_trades": len(trades),
        "win_rate_pct": round(win_rate, 1),
        "trades": df,
    }
