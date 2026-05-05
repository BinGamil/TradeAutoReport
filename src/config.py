"""Configuration helpers for the trading report project."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """Common filesystem locations used by the project."""

    root: Path

    @property
    def report_dir(self) -> Path:
        return self.root / "report"

    @property
    def markdown_reports_dir(self) -> Path:
        return self.report_dir / "markdown"

    @property
    def html_reports_dir(self) -> Path:
        return self.report_dir / "html"

    @property
    def today_html_report_path(self) -> Path:
        return self.report_dir / "StockReportAnalysisToday.html"

    @property
    def reports_dir(self) -> Path:
        return self.report_dir

    @property
    def prompts_dir(self) -> Path:
        return self.root / "prompts"


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATHS = ProjectPaths(root=PROJECT_ROOT)
DEFAULT_TICKER = "COST"
SUPPORTED_TICKERS = ("COST", "MSFT")
DEFAULT_PERIOD = "1y"
