"""
Simple, transparent trading strategy: SMA crossover for trend direction, RSI
for entry timing. Nothing exotic on purpose -- a bot handling real money
should use logic you can fully explain, not a black box.
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("trading_bot.strategy")


def compute_rsi(prices: pd.Series, period: int) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # avg_loss == 0 means no losses anywhere in the window: a strict uptrend
    # is maximally overbought (RSI 100), not neutral -- only truly flat
    # prices (avg_gain also 0) should read as neutral (RSI 50).
    rsi = rsi.where(avg_loss != 0, np.where(avg_gain > 0, 100.0, 50.0))

    return rsi.fillna(50)


def generate_signal(bars_df: pd.DataFrame, sma_fast: int, sma_slow: int,
                     rsi_period: int, rsi_oversold: float, rsi_overbought: float):
    """
    bars_df must have a 'close' column, oldest bar first.
    Returns "buy", "avoid", or "hold" plus a dict of diagnostic values.
    """
    if len(bars_df) < sma_slow + 1:
        return "hold", {"reason": "not enough price history yet"}

    close = bars_df["close"]
    sma_f = close.rolling(sma_fast).mean()
    sma_s = close.rolling(sma_slow).mean()
    rsi = compute_rsi(close, rsi_period)

    last_close = close.iloc[-1]
    last_sma_f = sma_f.iloc[-1]
    last_sma_s = sma_s.iloc[-1]
    last_rsi = rsi.iloc[-1]

    diagnostics = {
        "close": round(float(last_close), 2),
        "sma_fast": round(float(last_sma_f), 2),
        "sma_slow": round(float(last_sma_s), 2),
        "rsi": round(float(last_rsi), 2),
    }

    uptrend = last_sma_f > last_sma_s
    healthy_rsi = rsi_oversold <= last_rsi < rsi_overbought

    if uptrend and healthy_rsi:
        return "buy", diagnostics

    return "avoid", diagnostics
