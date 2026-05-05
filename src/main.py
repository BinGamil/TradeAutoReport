"""Command-line entry point for the daily premarket report MVP."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from dotenv import load_dotenv

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.config import DEFAULT_PERIOD, DEFAULT_TICKER, PATHS, SUPPORTED_TICKERS
    from src.deepseek_report import generate_trading_report
    from src.email_sender import send_report_email
    from src.html_report import save_combined_html_report, save_html_report
    from src.logger import get_logger
    from src.market_data import get_price_history
    from src.report_writer import save_markdown_report
    from src.technicals import atr14, macd, moving_average, rsi14
else:
    from .config import DEFAULT_PERIOD, DEFAULT_TICKER, PATHS, SUPPORTED_TICKERS
    from .deepseek_report import generate_trading_report
    from .email_sender import send_report_email
    from .html_report import save_combined_html_report, save_html_report
    from .logger import get_logger
    from .market_data import get_price_history
    from .report_writer import save_markdown_report
    from .technicals import atr14, macd, moving_average, rsi14

logger = get_logger(__name__)

TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")

load_dotenv(PATHS.root / ".env")


@dataclass
class ReportSummary:
    ticker: str
    latest_close: float
    previous_close: float
    daily_percent_change: float
    ma5: Optional[float]
    ma20: Optional[float]
    ma50: Optional[float]
    ma200: Optional[float]
    rsi14: Optional[float]
    macd_line: Optional[float]
    macd_signal: Optional[float]
    macd_histogram: Optional[float]
    atr14: Optional[float]


def _latest_value(series):
    cleaned = series.dropna()
    if cleaned.empty:
        return None
    value = cleaned.iloc[-1]
    if isinstance(value, pd.Series):
        if value.empty:
            return None
        value = value.iloc[-1]
    return float(value)


def build_summary(ticker: str = DEFAULT_TICKER, period: str = DEFAULT_PERIOD) -> ReportSummary:
    """Fetch price data and compute the key technical levels for a ticker."""

    data = get_price_history(ticker, period=period)
    if data.empty:
        raise RuntimeError(f"No market data available for {ticker}")

    close = data["Close"].astype(float)
    latest_close_value = close.iloc[-1]
    previous_close_value = close.iloc[-2] if len(close) >= 2 else latest_close_value
    if isinstance(latest_close_value, pd.Series):
        latest_close_value = latest_close_value.iloc[-1]
    if isinstance(previous_close_value, pd.Series):
        previous_close_value = previous_close_value.iloc[-1]
    latest_close = float(latest_close_value)
    previous_close = float(previous_close_value) if previous_close_value is not None else latest_close
    daily_percent_change = ((latest_close - previous_close) / previous_close) * 100 if previous_close else 0.0

    macd_frame = macd(data)
    summary = ReportSummary(
        ticker=ticker.upper(),
        latest_close=latest_close,
        previous_close=previous_close,
        daily_percent_change=daily_percent_change,
        ma5=_latest_value(moving_average(data, 5)),
        ma20=_latest_value(moving_average(data, 20)),
        ma50=_latest_value(moving_average(data, 50)),
        ma200=_latest_value(moving_average(data, 200)),
        rsi14=_latest_value(rsi14(data)),
        macd_line=_latest_value(macd_frame["macd_line"]),
        macd_signal=_latest_value(macd_frame["macd_signal"]),
        macd_histogram=_latest_value(macd_frame["macd_histogram"]),
        atr14=_latest_value(atr14(data)),
    )
    return summary


def _parse_tickers(raw_value: str | None) -> list[str]:
    """Read one or more ticker symbols from an environment value."""

    value = (raw_value or DEFAULT_TICKER).strip()
    if not value:
        return [DEFAULT_TICKER]

    if value.upper() == "ALL":
        return list(SUPPORTED_TICKERS)

    tickers: list[str] = []
    for part in value.replace(";", ",").split(","):
        ticker = part.strip().upper()
        if not ticker:
            continue
        if not TICKER_PATTERN.match(ticker):
            raise ValueError(f"Invalid ticker symbol: {ticker}")
        if ticker not in tickers:
            tickers.append(ticker)

    return tickers or [DEFAULT_TICKER]


def _get_run_settings() -> tuple[list[str], str]:
    """Read ticker symbols and report type from environment variables.

    GitHub Actions can inject these values for scheduled and manual runs,
    while local execution keeps the existing COST/premarket defaults.
    """

    ticker_value = os.getenv("REPORT_TICKERS") or os.getenv("REPORT_TICKER") or DEFAULT_TICKER
    tickers = _parse_tickers(ticker_value)
    report_type = os.getenv("REPORT_TYPE", "premarket").strip() or "premarket"
    return tickers, report_type.lower()


def _build_email_body(report_paths: list[str], html_paths: list[str]) -> str:
    """Build an email body from the generated Markdown report files."""

    sections: list[str] = [
        "Generated premarket trading report.",
        "",
        "The latest HTML report is attached as StockReportAnalysisToday.html.",
        "",
    ]

    for index, report_path in enumerate(report_paths, start=1):
        path = Path(report_path)
        sections.extend(
            [
                "=" * 72,
                f"Markdown Report {index}: {path.name}",
                "=" * 72,
                "",
            ]
        )
        try:
            sections.append(path.read_text(encoding="utf-8").strip())
        except Exception as exc:
            logger.exception("Unable to read Markdown report for email body: %s", exc)
            sections.append(f"Unable to read Markdown report body from {path}")
        sections.append("")

    if html_paths:
        sections.extend(
            [
                "=" * 72,
                "HTML Attachment",
                "=" * 72,
                *[Path(path).name for path in html_paths],
                "",
            ]
        )

    return "\n".join(sections).strip() + "\n"


def print_summary(summary: ReportSummary) -> None:
    """Print a compact technical snapshot to stdout."""

    print(f"Ticker: {summary.ticker}")
    print(f"Latest close: {summary.latest_close:.2f}")
    print(f"Previous close: {summary.previous_close:.2f}")
    print(f"Daily % change: {summary.daily_percent_change:.2f}%")
    print(f"MA5: {summary.ma5:.2f}" if summary.ma5 is not None else "MA5: N/A")
    print(f"MA20: {summary.ma20:.2f}" if summary.ma20 is not None else "MA20: N/A")
    print(f"MA50: {summary.ma50:.2f}" if summary.ma50 is not None else "MA50: N/A")
    print(f"MA200: {summary.ma200:.2f}" if summary.ma200 is not None else "MA200: N/A")
    print(f"RSI14: {summary.rsi14:.2f}" if summary.rsi14 is not None else "RSI14: N/A")
    if summary.macd_line is not None and summary.macd_signal is not None and summary.macd_histogram is not None:
        print(f"MACD line: {summary.macd_line:.4f}")
        print(f"MACD signal: {summary.macd_signal:.4f}")
        print(f"MACD histogram: {summary.macd_histogram:.4f}")
    else:
        print("MACD line: N/A")
        print("MACD signal: N/A")
        print("MACD histogram: N/A")
    print(f"ATR14: {summary.atr14:.2f}" if summary.atr14 is not None else "ATR14: N/A")


def main() -> int:
    """Entry point used by the CLI and future automation jobs."""

    report_paths: list[str] = []
    html_paths: list[str] = []
    html_report_items: list[dict[str, Any]] = []
    generated_tickers: list[str] = []
    failed_tickers: list[str] = []

    try:
        tickers, report_type = _get_run_settings()
    except Exception as exc:  # pragma: no cover - top-level guard
        logger.exception("Unable to read run settings: %s", exc)
        return 1

    for ticker in tickers:
        try:
            summary = build_summary(ticker=ticker)
            market_summary = {
                "ticker": summary.ticker,
                "latest_close": summary.latest_close,
                "previous_close": summary.previous_close,
                "daily_percent_change": summary.daily_percent_change,
            }
            indicators = {
                "ma5": summary.ma5,
                "ma20": summary.ma20,
                "ma50": summary.ma50,
                "ma200": summary.ma200,
                "rsi14": summary.rsi14,
                "macd_line": summary.macd_line,
                "macd_signal": summary.macd_signal,
                "macd_histogram": summary.macd_histogram,
                "atr14": summary.atr14,
            }
            report = generate_trading_report(
                ticker=summary.ticker,
                market_summary=market_summary,
                indicators=indicators,
                report_type=report_type,
            )
            report_path = save_markdown_report(
                ticker=summary.ticker,
                report_type=report_type,
                report=report,
            )
            generated_tickers.append(summary.ticker)
            report_paths.append(report_path)
            html_report_items.append(
                {
                    "ticker": summary.ticker,
                    "report": report,
                    "market_summary": market_summary,
                    "indicators": indicators,
                }
            )
        except Exception as exc:  # pragma: no cover - top-level guard
            failed_tickers.append(ticker)
            logger.exception("Unable to build report for %s: %s", ticker, exc)
            continue

    if not report_paths:
        logger.error("No reports were generated.")
        return 1

    try:
        if len(html_report_items) == 1:
            item = html_report_items[0]
            html_paths.append(
                save_html_report(
                    ticker=str(item["ticker"]),
                    report_type=report_type,
                    report=str(item["report"]),
                    market_summary=item["market_summary"],
                    indicators=item["indicators"],
                )
            )
        else:
            html_paths.append(
                save_combined_html_report(
                    reports=html_report_items,
                    report_type=report_type,
                )
            )
    except Exception:
        logger.exception("Unable to write HTML report; keeping the Markdown reports.")

    try:
        date_label = pd.Timestamp.now(tz="America/Toronto").strftime("%Y-%m-%d")
        ticker_label = ", ".join(generated_tickers)
        subject = f"{ticker_label} Premarket Trading Plan - {date_label}"
        email_body = _build_email_body(report_paths, html_paths)
        send_report_email(
            subject=subject,
            body=email_body,
            attachment_path=PATHS.today_html_report_path if html_paths else None,
        )
    except Exception:
        logger.exception("Unable to send report email; generated report files were kept.")

    print("\nGenerated Markdown reports:")
    for path in report_paths:
        print(f"- {path}")
    if html_paths:
        print("\nGenerated HTML reports:")
        for path in html_paths:
            print(f"- {path}")
    if failed_tickers:
        print(f"\nSkipped failed tickers: {', '.join(failed_tickers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
