"""Technical indicator calculations for daily price data."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _require_close(data: pd.DataFrame) -> pd.Series:
    if "Close" not in data.columns:
        raise ValueError("Price history must include a Close column")
    return data["Close"].astype(float)


def _require_high_low_close(data: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    for column in ("High", "Low", "Close"):
        if column not in data.columns:
            raise ValueError(f"Price history must include a {column} column")
    return (
        data["High"].astype(float),
        data["Low"].astype(float),
        data["Close"].astype(float),
    )


def moving_average(data: pd.DataFrame, window: int) -> pd.Series:
    """Calculate a simple moving average on the Close column."""

    close = _require_close(data)
    return close.rolling(window=window, min_periods=window).mean()


def rsi14(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate RSI using Wilder-style smoothing."""

    close = _require_close(data)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100.0)


def macd(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate MACD line, signal line, and histogram."""

    close = _require_close(data)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal

    return pd.DataFrame(
        {
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_histogram": macd_hist,
        },
        index=data.index,
    )


def atr14(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate the Average True Range."""

    high, low, close = _require_high_low_close(data)
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=period, min_periods=period).mean()
