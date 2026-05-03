"""Configuration helpers for the trading report project."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """Common filesystem locations used by the project."""

    root: Path

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    @property
    def prompts_dir(self) -> Path:
        return self.root / "prompts"


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATHS = ProjectPaths(root=PROJECT_ROOT)
DEFAULT_TICKER = "COST"
DEFAULT_PERIOD = "1y"
