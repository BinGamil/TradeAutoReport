"""Markdown report persistence helpers."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from .config import PATHS
from .logger import get_logger

logger = get_logger(__name__)

REPORT_TZ = ZoneInfo("America/Toronto")


def _report_filename(ticker: str, report_type: str, timestamp: datetime) -> str:
    safe_ticker = ticker.upper().strip()
    safe_report_type = report_type.strip().lower().replace(" ", "_")
    return f"{timestamp:%Y-%m-%d}_{safe_ticker}_{safe_report_type}.md"


def _build_header(ticker: str, report_type: str, timestamp: datetime) -> str:
    title = f"{ticker.upper()} {report_type.title()} Report"
    date_str = timestamp.strftime("%Y-%m-%d")
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
    return "\n".join(
        [
            f"# {title}",
            "",
            f"- Date: {date_str}",
            f"- Ticker: {ticker.upper()}",
            f"- Report Type: {report_type}",
            f"- Generated Timestamp: {timestamp_str}",
            "",
        ]
    )


def save_markdown_report(ticker: str, report_type: str, report: str) -> str:
    """Save a generated report as Markdown and return the file path."""

    timestamp = datetime.now(REPORT_TZ)
    reports_dir = PATHS.reports_dir
    reports_dir.mkdir(parents=True, exist_ok=True)

    file_name = _report_filename(ticker, report_type, timestamp)
    file_path = reports_dir / file_name
    content = _build_header(ticker, report_type, timestamp) + "\n" + report.strip() + "\n"

    try:
        file_path.write_text(content, encoding="utf-8")
    except Exception as exc:  # pragma: no cover - filesystem variability
        logger.exception("Failed to write report %s: %s", file_path, exc)
        raise

    return str(file_path)
