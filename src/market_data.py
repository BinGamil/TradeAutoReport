"""Market data access helpers."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from .logger import get_logger

logger = get_logger(__name__)


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Download daily OHLCV data for a ticker using yfinance.

    Returns an empty DataFrame if the download fails or no data is available.
    """

    try:
        data = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    except Exception as exc:  # pragma: no cover - network and provider errors vary
        logger.exception("Failed to download price history for %s: %s", ticker, exc)
        return pd.DataFrame()

    if data is None or data.empty:
        logger.warning("No price history returned for %s", ticker)
        return pd.DataFrame()

    data = data.copy()
    if isinstance(data.columns, pd.MultiIndex):
        if ticker in data.columns.get_level_values(-1):
            data = data.xs(ticker, axis=1, level=-1, drop_level=True)
        elif ticker in data.columns.get_level_values(0):
            data = data.xs(ticker, axis=1, level=0, drop_level=True)
        else:
            data.columns = [column[0] if isinstance(column, tuple) else column for column in data.columns]

    expected_columns = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
    if not expected_columns.intersection(set(data.columns)):
        logger.warning("Unexpected column layout returned for %s: %s", ticker, list(data.columns))
        return pd.DataFrame()

    data.index = pd.to_datetime(data.index)
    data.sort_index(inplace=True)
    return data
